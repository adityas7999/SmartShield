#include "smartshield/analyzer.hpp"

#include <algorithm>
#include <functional>
#include <map>
#include <set>
#include <sstream>

#include "smartshield/cfg.hpp"
#include "smartshield/ir_builder.hpp"

namespace smartshield {
namespace {
using json = nlohmann::json;
const std::vector<std::string> rules{"TXO-001", "REN-001", "ACC-001",
                                     "UEC-001"};
const std::map<std::string, std::string> titles{
    {"TXO-001", "Transaction origin used for authorization"},
    {"REN-001", "Checked storage updated after external interaction"},
    {"ACC-001", "Authority replacement without caller authorization"},
    {"UEC-001", "Low-level call failure is not handled"}};
const std::map<std::string, std::string> remedies{
    {"TXO-001",
     "Authenticate msg.sender against the intended trusted authority; test "
     "calls through intermediary contracts and define any delegation policy "
     "explicitly."},
    {"REN-001",
     "Apply checks-effects-interactions: update the identified storage "
     "location before the external call and handle failure. Consider a "
     "reviewed reentrancy guard across related entry points."},
    {"ACC-001",
     "Restrict authority replacement to the current authorized caller, "
     "validate the new address, and consider a two-step proposal/acceptance "
     "procedure."},
    {"UEC-001",
     "Bind the low-level success result and require/assert success, or "
     "implement an explicit failure branch before relying on the call's "
     "effects."}};

json span(const SourceLocation& l, const std::string& source) {
  int endLine = l.line, endColumn = l.column;
  for (std::size_t i = l.offset;
       l.available && i < l.offset + l.length && i < source.size(); ++i)
    if (source[i] == '\n') {
      ++endLine;
      endColumn = 1;
    } else
      ++endColumn;
  return {{"file", l.file},         {"offset", l.offset},
          {"length", l.length},     {"line", l.line},
          {"column", l.column},     {"endLine", endLine},
          {"endColumn", endColumn}, {"available", l.available}};
}
void expressions(const Expression& e,
                 const std::function<void(const Expression&)>& fn) {
  fn(e);
  for (const auto& child : e.children) expressions(child, fn);
}
void statements(const Statement& s,
                const std::function<void(const Statement&)>& fn) {
  fn(s);
  for (const auto& x : s.statements) statements(x, fn);
  for (const auto& x : s.then_body) statements(x, fn);
  for (const auto& x : s.else_body) statements(x, fn);
}
bool low(const Call& c) {
  return c.kind == CallKind::low_level || c.kind == CallKind::delegatecall ||
         c.kind == CallKind::staticcall;
}
bool external(const Call& c) {
  return low(c) || c.kind == CallKind::external_member ||
         c.kind == CallKind::transfer || c.kind == CallKind::send;
}
struct Storage {
  IrId base{};
  std::vector<std::string> keys;
  std::string member;
  SourceLocation location;
  std::string identity() const {
    std::string s = std::to_string(base) + member;
    for (const auto& k : keys) s += "[" + k + "]";
    return s;
  }
};
// Three-valued alias relation: 1 same, -1 different, 0 unresolved.
int alias(const Storage& a, const Storage& b) {
  if (a.base != b.base || a.member != b.member ||
      a.keys.size() != b.keys.size())
    return -1;
  bool unknown = false;
  for (const auto& key : a.keys)
    if (key.find("unresolved:") != std::string::npos) unknown = true;
  for (const auto& key : b.keys)
    if (key.find("unresolved:") != std::string::npos) unknown = true;
  for (std::size_t i = 0; i < a.keys.size(); ++i)
    if (a.keys[i] != b.keys[i]) {
      if (a.keys[i].starts_with("lit:") && b.keys[i].starts_with("lit:"))
        return -1;
      unknown = true;
    }
  return unknown ? 0 : 1;
}
struct Check {
  Storage storage;
  SourceLocation location;
};
struct Window {
  Check check;
  const Call* call;
};
struct Decision {
  const Expression* predicate;
  GraphNodeId node;
  bool truth;
  bool authorized{false};
};
struct Pending {
  const Call* call;
  bool handled{false};
  bool escaped{false};
};
struct State {
  std::map<IrId, std::string> values;
  std::map<IrId, std::vector<Storage>> dependencies;
  std::map<std::string, std::string> memory;
  std::vector<std::pair<std::string, std::string>> different;
  std::set<IrId> stale;
  std::map<std::string, bool> constraints;
  std::map<std::string, std::string> equalities;
  std::vector<Check> checks;
  std::vector<Window> windows;
  std::vector<Decision> decisions;
  std::map<std::string, Pending> pending;
  std::set<IrId> replaced;
  bool uncertain{false};
  std::map<std::string, json> candidates;
};
class Analysis {
  const Program& program;
  const std::string& source;
  const std::string& file;
  std::map<std::string, std::set<std::string>> reasons;
  std::map<std::string, json> findings;
  std::map<std::string, json>* active{};
  const Contract* contract{};
  const Function* function{};
  std::map<IrId, const Variable*> statevars;
  std::set<IrId> authorities;
  std::map<IrId, const Statement*> stmts;
  std::map<IrId, const Expression*> exprs;
  CfgGraph graph;
  std::size_t visits{};

 public:
  Analysis(const Program& p, const std::string& s, const std::string& f)
      : program(p), source(s), file(f) {}
  void unsupported(const std::string& rule, const std::string& why) {
    reasons[rule].insert((contract ? contract->name + "." : "") +
                         (function ? function->name + ": " : "") + why);
  }
  void unknown(const std::string& why) {
    for (const auto& r : rules) unsupported(r, why);
  }
  json evidence(const std::string& description,
                const SourceLocation& loc) const {
    return {{"description", description}, {"span", span(loc, source)}};
  }
  void finding(const std::string& rule, const SourceLocation& loc,
               const std::string& occurrence, const std::string& explanation,
               json ev) {
    const std::string id = rule + ":" + std::to_string(contract->id) + ":" +
                           std::to_string(function->id) + ":" + occurrence;
    auto& output = *active;
    if (output.contains(id)) {
      auto& old = output[id]["evidence"];
      for (const auto& e : ev)
        if (std::find(old.begin(), old.end(), e) == old.end()) old.push_back(e);
      return;
    }
    output[id] = {
        {"id", id},
        {"ruleId", rule},
        {"title", titles.at(rule)},
        {"severity", rule == "UEC-001" ? "medium" : "high"},
        {"confidence", rule == "REN-001" ? "medium" : "high"},
        {"contract", contract->name},
        {"function", function->name},
        {"primarySpan", span(loc, source)},
        {"evidence", ev},
        {"explanation", explanation},
        {"limitations",
         json::array(
             {rule == "REN-001"
                  ? "Abstract path establishes a structural window only; "
                    "callback feasibility, gas, target behavior and "
                    "exploitability are not proven."
                  : "Conclusion is bounded by the supported intraprocedural "
                    "model; this is not a complete security audit."})},
        {"remediation", remedies.at(rule)}};
  }
  std::string value(const Expression& e, const State& st) const {
    if (e.kind == ExpressionKind::builtin) return e.name;
    if (e.kind == ExpressionKind::literal) {
      // Semantic rational types normalize decimal/hex spelling and denomination
      // units.
      if (e.type_identifier.starts_with("t_rational_") &&
          e.type_identifier.ends_with("_by_1"))
        return "lit:" +
               e.type_identifier.substr(11, e.type_identifier.size() - 16);
      return "lit:" + e.name;
    }
    if (auto place = storage(e, st)) {
      auto key = place->identity();
      if (st.memory.contains(key)) return st.memory.at(key);
      return "storage:" + key;
    }
    if (e.kind == ExpressionKind::identifier) {
      if (st.values.contains(e.variable)) return st.values.at(e.variable);
      return e.variable ? "v:" + std::to_string(e.variable)
                        : "unresolved:" + e.type_identifier + ":" + e.name;
    }
    if (e.conversion && e.children.size() == 2) return value(e.children[1], st);
    if (e.kind == ExpressionKind::call) return "call:" + std::to_string(e.id);
    if (e.kind == ExpressionKind::unary && e.op == "!")
      return "!(" + value(e.children[0], st) + ")";
    std::string result =
        std::to_string(static_cast<int>(e.kind)) + ":" + e.name + e.op + "(";
    for (const auto& child : e.children) result += value(child, st) + ",";
    return result + ")";
  }
  std::optional<Storage> storage(const Expression& e, const State& st) const {
    if (e.kind == ExpressionKind::identifier && statevars.contains(e.variable))
      return Storage{e.variable, {}, "", e.location};
    if ((e.kind == ExpressionKind::index || e.kind == ExpressionKind::member) &&
        !e.children.empty()) {
      auto s = storage(e.children[0], st);
      if (!s) return {};
      if (e.kind == ExpressionKind::index && e.children.size() == 2)
        s->keys.push_back(value(e.children[1], st));
      else
        s->member += "." + e.name;
      s->location = e.location;
      return s;
    }
    return {};
  }
  std::vector<Storage> reads(const Expression& e, const State& st) const {
    if (auto s = storage(e, st)) return {*s};
    if (e.kind == ExpressionKind::identifier &&
        st.dependencies.contains(e.variable))
      return st.dependencies.at(e.variable);
    std::vector<Storage> out;
    for (const auto& c : e.children) {
      auto r = reads(c, st);
      out.insert(out.end(), r.begin(), r.end());
    }
    return out;
  }
  bool constrain(const Expression& e, bool truth, State& st) {
    if (e.kind == ExpressionKind::unary && e.op == "!")
      return constrain(e.children[0], !truth, st);
    if (e.kind == ExpressionKind::literal &&
        (e.name == "true" || e.name == "false"))
      return (e.name == "true") == truth;
    std::string atom = value(e, st);
    if (e.kind == ExpressionKind::binary && e.children.size() == 2) {
      auto a = value(e.children[0], st), b = value(e.children[1], st);
      auto op = e.op;
      if (op == "!=") {
        op = "==";
        truth = !truth;
      }
      if (op == ">=") {
        op = "<";
        truth = !truth;
      }
      if (op == "<=") {
        op = ">";
        truth = !truth;
      }
      if ((op == "<" || op == ">") && a.starts_with("lit:") &&
          b.starts_with("lit:")) {
        auto left = a.substr(4), right = b.substr(4);
        const auto decimal = [](const auto& x) {
          return !x.empty() &&
                 x.find_first_not_of("0123456789") == std::string::npos;
        };
        if (decimal(left) && decimal(right)) {
          const bool less = left.size() != right.size()
                                ? left.size() < right.size()
                                : left < right;
          const bool greater = left.size() != right.size()
                                   ? left.size() > right.size()
                                   : left > right;
          return (op == "<" ? less : greater) == truth;
        }
      }
      if (op == "==") {
        auto root = [&](std::string x) {
          std::set<std::string> seen;
          while (st.equalities.contains(x) && seen.insert(x).second)
            x = st.equalities[x];
          return x;
        };
        a = root(a);
        b = root(b);
        if (a == b) return truth;
        if (a.starts_with("lit:") && b.starts_with("lit:")) return !truth;
        if (b == "lit:true" || b == "lit:false") {
          atom = a;
          truth = truth == (b == "lit:true");
        } else if (a == "lit:true" || a == "lit:false") {
          atom = b;
          truth = truth == (a == "lit:true");
        } else {
          if (a > b) std::swap(a, b);
          atom = a + "==" + b;
          if (truth) {
            // Union symbolic identities, preferring a literal as
            // representative.
            auto from = a, to = b;
            if (a.starts_with("lit:")) {
              from = b;
              to = a;
            }
            st.equalities[from] = to;
            for (const auto& [x, y] : st.different)
              if (root(x) == root(y)) return false;
          } else
            st.different.push_back({a, b});
        }
      } else
        atom = a + op + b;
    }
    while (atom.starts_with("!(") && atom.ends_with(")")) {
      atom = atom.substr(2, atom.size() - 3);
      truth = !truth;
    }
    if (atom == "lit:true" || atom == "lit:false")
      return (atom == "lit:true") == truth;
    if (st.constraints.contains(atom)) return st.constraints[atom] == truth;
    st.constraints[atom] = truth;
    return true;
  }
  bool effective_auth(const State& st) const {
    for (const auto& d : st.decisions)
      if (d.authorized) return true;
    return false;
  }
  bool auth_predicate(const Expression& e, bool truth, const State& st) const {
    if (e.kind == ExpressionKind::unary && e.op == "!")
      return auth_predicate(e.children[0], !truth, st);
    if (e.kind == ExpressionKind::tuple && e.children.size() == 1)
      return auth_predicate(e.children[0], truth, st);
    if (e.kind != ExpressionKind::binary || e.children.size() != 2 ||
        !((e.op == "==" && truth) || (e.op == "!=" && !truth)))
      return false;
    for (int i = 0; i < 2; ++i)
      if (value(e.children[i], st) == "msg.sender") {
        const auto& other = e.children[1 - i];
        // Literal address restrictions and direct local identity aliases are
        // supported.
        if (value(other, st).starts_with("lit:")) return true;
        const auto dependencies = reads(other, st);
        if (dependencies.size() == 1 && dependencies[0].keys.empty() &&
            dependencies[0].member.empty() &&
            authorities.contains(dependencies[0].base) &&
            !st.replaced.contains(dependencies[0].base))
          return true;
      }
    return false;
  }
  bool unresolved_authorization(const State& st, GraphNodeId node) const {
    for (const auto& d : st.decisions) {
      if (d.authorized || reads(*d.predicate, st).empty()) continue;
      const auto& predicate = *d.predicate;
      bool replaced_identity = false;
      if (predicate.kind == ExpressionKind::binary &&
          predicate.children.size() == 2 &&
          (predicate.op == "==" || predicate.op == "!=")) {
        for (int i = 0; i < 2; ++i)
          if (value(predicate.children[i], st) == "msg.sender") {
            const auto dependencies = reads(predicate.children[1 - i], st);
            if (dependencies.size() == 1 &&
                authorities.contains(dependencies[0].base) &&
                st.replaced.contains(dependencies[0].base))
              replaced_identity = true;
          }
      }
      if (replaced_identity) continue;
      bool origin = false;
      expressions(*d.predicate, [&](const auto& e) {
        if (e.kind == ExpressionKind::builtin && e.name == "tx.origin")
          origin = true;
      });
      if (origin)
        continue;  // Known ineffective origin identity guard, not an unknown
                   // caller restriction.
      const auto other = graph.branch_reachable(
          d.node,
          d.truth ? CfgEdgeKind::false_branch : CfgEdgeKind::true_branch, node);
      if (other.status == QueryStatus::no) return true;
    }
    return false;
  }
  void txo(const Statement& s, GraphNodeId node, const State& st) {
    bool effect =
        std::any_of(
            s.state_accesses.begin(), s.state_accesses.end(),
            [](const auto& a) { return a.action == AccessKind::write; }) ||
        std::any_of(s.calls.begin(), s.calls.end(), [](const auto& c) {
          return external(c) ||
                 (c.kind == CallKind::builtin && c.name == "selfdestruct");
        });
    if (!effect) return;
    for (const auto& d : st.decisions) {
      const Expression* predicate = d.predicate;
      while (
          (predicate->kind == ExpressionKind::unary && predicate->op == "!") ||
          (predicate->kind == ExpressionKind::tuple &&
           predicate->children.size() == 1))
        predicate = &predicate->children[0];
      const auto& e = *predicate;
      if (e.kind != ExpressionKind::binary || e.children.size() != 2 ||
          (e.op != "==" && e.op != "!="))
        continue;
      for (int i = 0; i < 2; ++i)
        if (e.children[i].kind == ExpressionKind::builtin &&
            e.children[i].name == "tx.origin") {
          const auto& authority = e.children[1 - i];
          if (authority.kind != ExpressionKind::identifier ||
              !authorities.contains(authority.variable)) {
            unsupported("TXO-001", "Origin comparison authority is unresolved");
            continue;
          }
          const auto other = graph.branch_reachable(
              d.node,
              d.truth ? CfgEdgeKind::false_branch : CfgEdgeKind::true_branch,
              node);
          if (other.status != QueryStatus::no) continue;
          finding(
              "TXO-001", e.children[i].location, std::to_string(e.id),
              "A tx.origin identity guard controls this state-changing or "
              "external operation; its opposite CFG edge cannot reach the "
              "operation.",
              json::array(
                  {evidence("Origin identity used by guard",
                            e.children[i].location),
                   evidence("Controlling authorization predicate", e.location),
                   evidence("Operation restricted by guard", s.location)}));
        }
    }
  }
  void flush(State& st, const SourceLocation& exit) {
    active = &st.candidates;
    if (st.uncertain) return;
    for (auto& [symbol, p] : st.pending) {
      if (p.handled || p.escaped) continue;
      if (st.constraints.contains(symbol) && st.constraints[symbol]) continue;
      finding("UEC-001", p.call->location, std::to_string(p.call->expression),
              "A low-level call can reach normal continuation without checking "
              "or explicitly handling its failure result.",
              json::array(
                  {evidence("Typed low-level external call", p.call->location),
                   evidence("Normal continuation with unhandled success result",
                            exit)}));
      if (p.call->kind == CallKind::delegatecall) {
        const std::string id = "UEC-001:" + std::to_string(contract->id) + ":" +
                               std::to_string(function->id) + ":" +
                               std::to_string(p.call->expression);
        (*active)[id]["severity"] = "high";
      }
    }
  }
  void process(const Statement& s, GraphNodeId node, State& st) {
    active = &st.candidates;
    if (st.uncertain) return;
    const bool mixed = std::any_of(s.calls.begin(), s.calls.end(), external) &&
                       std::any_of(s.state_accesses.begin(),
                                   s.state_accesses.end(), [](const auto& a) {
                                     return a.action == AccessKind::write;
                                   });
    if (mixed) {
      unknown(
          "External interaction and storage write share unresolved statement "
          "order");
      st.uncertain = true;
      return;
    }
    txo(s, node, st);
    // Explicit effects/return on a known failure branch count as local failure
    // handling.
    if (s.kind == StatementKind::emit ||
        s.kind == StatementKind::return_statement ||
        std::any_of(
            s.state_accesses.begin(), s.state_accesses.end(),
            [](const auto& a) { return a.action == AccessKind::write; }))
      for (auto& [symbol, p] : st.pending)
        if (st.constraints.contains(symbol) && !st.constraints[symbol]) {
          for (const auto& d : st.decisions) {
            bool uses = false;
            expressions(*d.predicate, [&](const auto& e) {
              if (value(e, st) == symbol || value(e, st) == "!(" + symbol + ")")
                uses = true;
            });
            if (uses &&
                graph.branch_reachable(d.node,
                                       d.truth ? CfgEdgeKind::false_branch
                                               : CfgEdgeKind::true_branch,
                                       node)
                        .status == QueryStatus::no)
              p.handled = true;
          }
        }
    for (const auto& a : s.state_accesses)
      if (a.action == AccessKind::write && exprs.contains(a.expression)) {
        const auto location = storage(*exprs[a.expression], st);
        if (!location) continue;
        if (authorities.contains(a.variable) && !effective_auth(st) &&
            unresolved_authorization(st, node))
          unsupported(
              "ACC-001",
              "A state-dependent restriction controls authority replacement "
              "but its authorization semantics are unresolved");
        if (authorities.contains(a.variable) && !effective_auth(st) &&
            !unresolved_authorization(st, node))
          finding("ACC-001", a.location, std::to_string(a.expression),
                  "A supported path from a public/external entry point "
                  "replaces a designated authority without an effective "
                  "immediate-caller restriction.",
                  json::array(
                      {evidence("Designated address authority declaration",
                                statevars[a.variable]->location),
                       evidence("Reachable authority replacement", a.location),
                       evidence("Public/external entry point",
                                function->location)}));
        st.replaced.insert(a.variable);
        for (const auto& window : st.windows) {
          const int relation = alias(window.check.storage, *location);
          if (relation == 0)
            unsupported("REN-001",
                        "Storage keys may alias but equality is unresolved");
          if (relation == 1 && window.call->statement != s.id)
            finding("REN-001", window.call->location,
                    std::to_string(window.call->expression) + ":" +
                        location->identity(),
                    "A represented path checks this storage location, "
                    "interacts externally, then updates the same location "
                    "before any earlier effects update resolved the check.",
                    json::array(
                        {evidence("Eligibility/balance check of storage " +
                                      location->identity(),
                                  window.check.location),
                         evidence("External interaction before the update",
                                  window.call->location),
                         evidence("Later write to the same storage location",
                                  a.location)}));
        }
        st.checks.erase(std::remove_if(st.checks.begin(), st.checks.end(),
                                       [&](const auto& c) {
                                         return alias(c.storage, *location) !=
                                                -1;
                                       }),
                        st.checks.end());
        st.windows.erase(std::remove_if(st.windows.begin(), st.windows.end(),
                                        [&](const auto& w) {
                                          return alias(w.check.storage,
                                                       *location) != -1;
                                        }),
                         st.windows.end());
        for (auto& [id, deps] : st.dependencies) {
          if (std::any_of(deps.begin(), deps.end(), [&](const auto& dep) {
                return alias(dep, *location) != -1;
              })) {
            st.stale.insert(id);
            deps.clear();
          }
        }
        std::string updated = "write:" + std::to_string(a.id);
        for (const auto& e : s.expressions)
          if (e.kind == ExpressionKind::assignment && e.op == "=" &&
              e.children[0].id == a.expression)
            updated = value(e.children[1], st);
        st.memory[location->identity()] = updated;
      }
    for (const auto& c : s.calls) {
      if (low(c)) st.pending["call:" + std::to_string(c.expression)] = {&c};
      bool callback = external(c) && c.kind != CallKind::staticcall;
      if (c.kind == CallKind::external_member && exprs.contains(c.expression)) {
        const auto& e = *exprs[c.expression];
        const auto& t = e.children[0].type_identifier;
        if (t.find("_view") != std::string::npos ||
            t.find("_pure") != std::string::npos)
          callback = false;
      }
      if (callback) {
        bool writes = std::any_of(
            s.state_accesses.begin(), s.state_accesses.end(),
            [](const auto& a) { return a.action == AccessKind::write; });
        if (writes)
          unsupported("REN-001",
                      "Call and state write share a statement with unresolved "
                      "effect order");
        else
          for (const auto& check : st.checks) st.windows.push_back({check, &c});
      }
    }
    auto assign = [&](IrId variable, const Expression& rhs) {
      bool transformed = false;
      expressions(rhs, [&](const auto& part) {
        if (part.kind == ExpressionKind::binary) transformed = true;
      });
      if (transformed)
        expressions(rhs, [&](const auto& part) {
          const auto symbol = value(part, st);
          if (st.pending.contains(symbol)) {
            st.pending[symbol].escaped = true;
            unsupported("UEC-001",
                        "Boolean result transformation is outside supported "
                        "alias/negation flow");
          }
        });
      st.values[variable] = value(rhs, st);
      st.dependencies[variable] = reads(rhs, st);
    };
    if (s.kind == StatementKind::declaration && !s.expressions.empty() &&
        !s.declarations.empty()) {
      const auto& rhs = s.expressions[0];
      assign(s.declarations[0].id, rhs);
      for (std::size_t i = 1; i < s.declarations.size(); ++i)
        st.values[s.declarations[i].id] =
            "unknown:" + std::to_string(s.declarations[i].id);
    }
    for (const auto& e : s.expressions) {
      if (e.kind == ExpressionKind::assignment && e.children.size() == 2) {
        const auto& lhs = e.children[0];
        const auto& rhs = e.children[1];
        if (lhs.kind == ExpressionKind::identifier) {
          if (e.op == "=")
            assign(lhs.variable, rhs);
          else {
            st.values[lhs.variable] = "version:" + std::to_string(e.id);
            st.dependencies.erase(lhs.variable);
          }
        } else if (lhs.kind == ExpressionKind::tuple && !lhs.children.empty() &&
                   lhs.children[0].kind == ExpressionKind::identifier)
          assign(lhs.children[0].variable, rhs);
      }
      if (s.kind == StatementKind::return_statement)
        expressions(e, [&](const auto& x) {
          auto symbol = value(x, st);
          if (st.pending.contains(symbol)) {
            st.pending[symbol].escaped = true;
            unsupported("UEC-001",
                        "Call result returned to caller; caller handling is "
                        "unresolved");
          }
        });
    }
  }
  void traverse(GraphNodeId node, State st) {
    if (++visits > 4096) {
      unknown("CFG traversal bound (4096 node visits) exceeded");
      return;
    }
    const auto* n = graph.node(node);
    if (!n) return;
    if (n->kind == CfgNodeKind::exceptional_exit) return;
    if (n->kind == CfgNodeKind::normal_exit) {
      flush(st, function->location);
      for (const auto& [id, f] : st.candidates) {
        if (!findings.contains(id))
          findings[id] = f;
        else
          for (const auto& e : f["evidence"]) {
            auto& ev = findings[id]["evidence"];
            if (std::find(ev.begin(), ev.end(), e) == ev.end()) ev.push_back(e);
          }
      }
      return;
    }
    if (stmts.contains(n->statement)) process(*stmts[n->statement], node, st);
    for (const auto& edge : graph.edges)
      if (edge.from == node) {
        auto next = st;
        if (n->predicate && exprs.contains(n->predicate) &&
            (edge.kind == CfgEdgeKind::true_branch ||
             edge.kind == CfgEdgeKind::false_branch)) {
          const auto& e = *exprs[n->predicate];
          bool truth = edge.kind == CfgEdgeKind::true_branch;
          if (!constrain(e, truth, next)) continue;
          next.decisions.push_back(
              {&e, node, truth, auth_predicate(e, truth, next)});
          if (truth && stmts.contains(n->statement) &&
              (stmts[n->statement]->kind == StatementKind::require_guard ||
               stmts[n->statement]->kind == StatementKind::assert_guard)) {
            expressions(e, [&](const auto& part) {
              auto symbol = value(part, next);
              if (next.pending.contains(symbol))
                next.pending[symbol].handled = true;
            });
          }
          expressions(e, [&](const auto& part) {
            if (next.stale.contains(part.variable))
              unsupported("REN-001",
                          "An eligibility check uses a local snapshot from "
                          "before a storage update");
          });
          for (const auto& storage : reads(e, next))
            next.checks.push_back({storage, e.location});
        }
        traverse(edge.to, std::move(next));
      }
  }
  void run_function(const Function& f) {
    function = &f;
    if (!f.body || f.name == "constructor" ||
        (f.visibility != "public" && f.visibility != "external"))
      return;
    if (contract->inherited) {
      unknown("Inherited declarations/restrictions are not resolved");
      return;
    }
    if (std::any_of(f.modifiers.begin(), f.modifiers.end(), [](const auto& m) {
          return m.resolution != Resolution::resolved;
        })) {
      unknown(
          "Modifier cannot be expanded by the supported guard-prefix model");
      return;
    }
    stmts.clear();
    exprs.clear();
    bool blocked = false;
    statements(*f.body, [&](const Statement& s) {
      stmts[s.id] = &s;
      if (s.kind == StatementKind::unsupported) {
        unknown("Unsupported statement/control flow");
        blocked = true;
      }
      for (const auto& v : s.declarations)
        if (v.storage == "storage") {
          unknown("Storage alias is unresolved");
          blocked = true;
        }
      for (const auto& c : s.calls)
        if (c.kind == CallKind::internal || c.kind == CallKind::unknown) {
          unknown(
              "Internal/library/dynamic callee effects and restrictions are "
              "unresolved");
          blocked = true;
        }
      for (const auto& e : s.expressions)
        expressions(e, [&](const Expression& x) {
          exprs[x.id] = &x;
          if (x.kind == ExpressionKind::assignment && !x.children.empty() &&
              x.children[0].kind == ExpressionKind::tuple) {
            for (const auto& lhs : x.children[0].children)
              if (storage(lhs, State{})) {
                unknown("Tuple assignment storage effects are unresolved");
                blocked = true;
              }
          }
          if ((s.kind == StatementKind::declaration ||
               x.kind == ExpressionKind::assignment) &&
              x.kind != ExpressionKind::unknown) {
            bool origin = false;
            expressions(x, [&](const auto& part) {
              if (part.kind == ExpressionKind::builtin &&
                  part.name == "tx.origin")
                origin = true;
            });
            if (origin)
              unsupported("TXO-001",
                          "Origin value copied through local/state data flow; "
                          "authorization use is unresolved");
          }
          if (x.resolution == Resolution::unsupported || x.op == "&&" ||
              x.op == "||") {
            unknown("Unsupported expression or composite predicate");
            blocked = true;
          }
          if (x.kind == ExpressionKind::unary &&
              (x.op == "++" || x.op == "--")) {
            unknown(
                "Increment/decrement data flow is outside the bounded model");
            blocked = true;
          }
        });
    });
    if (blocked) return;
    graph = build_cfg(f);
    visits = 0;
    traverse(graph.entry, State{});
  }
  json run() {
    if (!program.typed)
      unknown(
          "A type-checked solc AST is required; parsing-only input is "
          "unsupported");
    else
      for (const auto& c : program.contracts) {
        contract = &c;
        function = nullptr;
        statevars.clear();
        authorities.clear();
        for (const auto& v : c.variables) {
          statevars[v.id] = &v;
          if ((v.type == "address" || v.type == "address payable") &&
              (v.name == "owner" || v.name == "admin" ||
               v.name == "administrator"))
            authorities.insert(v.id);
        }
        for (const auto& f : c.functions)
          if (f.body)
            statements(*f.body, [&](const Statement& s) {
              if (!s.predicate) return;
              for (const auto& e : s.expressions)
                expressions(e, [&](const Expression& x) {
                  if (x.kind != ExpressionKind::binary ||
                      x.children.size() != 2 || (x.op != "==" && x.op != "!="))
                    return;
                  for (int i = 0; i < 2; ++i)
                    if (x.children[i].kind == ExpressionKind::builtin &&
                        (x.children[i].name == "msg.sender" ||
                         x.children[i].name == "tx.origin")) {
                      const auto v = x.children[1 - i].variable;
                      if (statevars.contains(v) &&
                          (statevars[v]->type == "address" ||
                           statevars[v]->type == "address payable"))
                        authorities.insert(v);
                    }
                });
            });
        for (const auto& f : c.functions) run_function(f);
      }
    json fs = json::array(), rs = json::array(), byRule = json::object(),
         bySeverity = {{"high", 0}, {"medium", 0}, {"low", 0}};
    bool partial = false;
    for (const auto& r : rules) {
      byRule[r] = 0;
      const bool unsupported = !reasons[r].empty();
      partial |= unsupported;
      rs.push_back({{"ruleId", r},
                    {"status", unsupported ? "unsupported" : "completed"},
                    {"reasons", reasons[r]}});
    }
    for (const auto& [id, f] : findings) {
      fs.push_back(f);
      byRule[f["ruleId"].get<std::string>()] =
          byRule[f["ruleId"].get<std::string>()].get<int>() + 1;
      bySeverity[f["severity"].get<std::string>()] =
          bySeverity[f["severity"].get<std::string>()].get<int>() + 1;
    }
    return {
        {"schemaVersion", "1.0.0"},
        {"reportVersion", "1.0.0"},
        {"status", partial ? "partial" : "completed"},
        {"source", {{"fileName", file}, {"byteLength", source.size()}}},
        {"compilerErrors", json::array()},
        {"ruleResults", rs},
        {"findings", fs},
        {"summary",
         {{"total", fs.size()},
          {"byRule", byRule},
          {"bySeverity", bySeverity}}},
        {"analysisLimitations",
         json::array(
             {"Four bounded rules only. Zero findings is not a security "
              "guarantee.",
              "Abstract path consistency is not full arithmetic satisfiability "
              "or exploitability proof.",
              "Interprocedural effects, inheritance, loops, assembly, complex "
              "modifiers and storage aliases require unsupported coverage."})}};
  }
};
}  // namespace
nlohmann::json Analyzer::analyze(const nlohmann::json& output,
                                 const std::string& source,
                                 const std::string& file) const {
  const auto program = build_ir(output, source, file);
  return Analysis(program, source, file).run();
}
}  // namespace smartshield
