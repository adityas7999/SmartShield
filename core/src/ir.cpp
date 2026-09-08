#include "smartshield/ir_builder.hpp"

#include <algorithm>
#include <charconv>
#include <stdexcept>
#include <unordered_map>
#include <nlohmann/json.hpp>

namespace smartshield {
namespace {
using json = nlohmann::json;

// The parser-only AST has no reliable referencedDeclaration or stateVariable flag.
// Resolve direct declarations lexically. Never infer storage from a variable name alone.
class Builder {
 public:
  Builder(const std::string& source, const std::string& file)
      : source_(source), file_(file) {
    line_starts_.push_back(0);
    for (std::size_t i = 0; i < source.size(); ++i)
      if (source[i] == '\n') line_starts_.push_back(i + 1);
  }

  Program build(const json& output) {
    if (output.contains("errors"))
      for (const auto& error : output.at("errors"))
        if (error.value("severity", "") == "error")
          throw std::runtime_error("Cannot build IR from compiler errors");
    if (!output.contains("sources") || !output.at("sources").contains(file_))
      throw std::runtime_error("Requested source is missing from compiler output");
    const auto& entry = output.at("sources").at(file_);
    if (!entry.contains("ast") || entry.at("ast").value("nodeType", "") != "SourceUnit")
      throw std::runtime_error("Requested source has no SourceUnit AST");
    for (const auto& node : entry.at("ast").at("nodes")) {
      if (node.value("nodeType", "") == "ContractDefinition")
        program_.contracts.push_back(contract(node));
      else if (node.value("nodeType", "") != "PragmaDirective")
        note(no_id, location(node), "Source-level " + node.value("nodeType", "unknown") + " is unsupported");
    }
    return std::move(program_);
  }

 private:
  struct Binding { IrId id; VariableKind kind; };
  const std::string& source_;
  const std::string& file_;
  std::vector<std::size_t> line_starts_;
  std::vector<std::unordered_map<std::string, Binding>> scopes_;
  std::unordered_map<std::string, bool> function_names_;
  Program program_;
  IrId next_id_{1};
  IrId function_id_{no_id};

  void note(IrId id, const SourceLocation& loc, const std::string& message) {
    program_.limitations.push_back({id, loc, message});
  }

  SourceLocation location(const json& node) const {
    SourceLocation loc;
    loc.file = file_;
    const auto src = node.value("src", "");
    const auto first = src.find(':');
    const auto second = first == std::string::npos ? first : src.find(':', first + 1);
    if (second == std::string::npos) return loc;
    const auto offset = std::from_chars(src.data(), src.data() + first, loc.offset);
    const auto length = std::from_chars(src.data() + first + 1, src.data() + second, loc.length);
    if (offset.ec != std::errc{} || offset.ptr != src.data() + first ||
        length.ec != std::errc{} || length.ptr != src.data() + second ||
        loc.offset > source_.size() || loc.length > source_.size() - loc.offset) return loc;
    const auto line = std::upper_bound(line_starts_.begin(), line_starts_.end(), loc.offset);
    loc.line = static_cast<int>(line - line_starts_.begin());
    loc.column = static_cast<int>(loc.offset - *(line - 1)) + 1;
    loc.available = true;
    return loc;
  }

  std::string text(const SourceLocation& loc) const {
    return loc.available ? source_.substr(loc.offset, loc.length) : "";
  }

  std::optional<Binding> lookup(const std::string& name) const {
    for (auto it = scopes_.rbegin(); it != scopes_.rend(); ++it) {
      const auto found = it->find(name);
      if (found != it->end()) return found->second;
    }
    return std::nullopt;
  }

  Variable variable(const json& node, VariableKind kind) {
    Variable v;
    v.id = next_id_++;
    v.name = node.value("name", "");
    v.kind = kind;
    v.location = location(node);
    v.storage = node.value("storageLocation", "default");
    if (node.contains("typeName")) v.type = text(location(node.at("typeName")));
    if (!v.name.empty()) scopes_.back()[v.name] = {v.id, kind};
    if (v.storage == "storage" && kind != VariableKind::state)
      note(v.id, v.location, "Storage alias is not resolved");
    return v;
  }

  Expression expression(const json& node) {
    Expression e;
    e.id = next_id_++;
    if (node.is_null()) return e; // Preserve empty tuple positions.
    e.location = location(node);
    e.text = text(e.location);
    e.op = node.value("operator", "");
    e.prefix = node.value("prefix", true);
    e.resolution = Resolution::syntax_only;
    const auto type = node.value("nodeType", "");
    auto child = [&](const char* key) { e.children.push_back(expression(node.at(key))); };
    if (type == "Identifier") {
      e.kind = ExpressionKind::identifier;
      e.name = node.value("name", "");
      if (const auto binding = lookup(e.name)) {
        e.variable = binding->id;
        e.resolution = Resolution::resolved;
      } else {
        e.resolution = Resolution::unresolved;
      }
    } else if (type == "Literal") {
      e.kind = ExpressionKind::literal;
      e.name = node.value("value", "");
    } else if (type == "MemberAccess") {
      e.kind = ExpressionKind::member;
      e.name = node.value("memberName", "");
      child("expression");
      const auto& base = e.children.front();
      if (base.kind == ExpressionKind::identifier && base.variable == no_id &&
          ((base.name == "tx" && e.name == "origin") ||
           (base.name == "msg" && (e.name == "sender" || e.name == "value")))) {
        e.kind = ExpressionKind::builtin;
        e.name = base.name + "." + e.name;
      }
    } else if (type == "IndexAccess") {
      e.kind = ExpressionKind::index;
      child("baseExpression"); child("indexExpression");
    } else if (type == "BinaryOperation" || type == "Assignment") {
      const bool assignment = type == "Assignment";
      e.kind = assignment ? ExpressionKind::assignment : ExpressionKind::binary;
      child(assignment ? "leftHandSide" : "leftExpression");
      child(assignment ? "rightHandSide" : "rightExpression");
      if (e.op == "&&" || e.op == "||")
        note(e.id, e.location, "Short-circuit operands are preserved; conditional effect paths need expression-level CFG support");
    } else if (type == "UnaryOperation") {
      e.kind = ExpressionKind::unary; child("subExpression");
    } else if (type == "FunctionCall" || type == "FunctionCallOptions") {
      const bool options = type == "FunctionCallOptions";
      e.kind = options ? ExpressionKind::call_options : ExpressionKind::call;
      child("expression");
      for (const auto& arg : node.at(options ? "options" : "arguments"))
        e.children.push_back(expression(arg));
      e.names = node.value("names", std::vector<std::string>{});
    } else if (type == "TupleExpression") {
      e.kind = ExpressionKind::tuple;
      for (const auto& item : node.at("components")) e.children.push_back(expression(item));
    } else if (type == "ElementaryTypeNameExpression") {
      e.kind = ExpressionKind::type;
    } else {
      e.resolution = Resolution::unsupported;
      note(e.id, e.location, "Unsupported expression: " + type);
    }
    if (!e.location.available) note(e.id, e.location, "Expression source range is unavailable");
    return e;
  }

  void collect_call(const Expression& e, Statement& s) {
    const Expression* callee = &e.children.at(0);
    Call call;
    call.id = next_id_++; call.expression = e.id;
    call.statement = s.id; call.function = function_id_; call.location = e.location;
    call.resolution = Resolution::syntax_only;
    if (callee->kind == ExpressionKind::call_options) {
      for (std::size_t i = 0; i < callee->names.size() && i + 1 < callee->children.size(); ++i)
        if (callee->names[i] == "value") call.value = callee->children[i + 1].id;
      callee = &callee->children.at(0);
    }
    call.name = callee->name;
    call.target = callee->id;
    for (std::size_t i = 1; i < e.children.size(); ++i) call.arguments.push_back(e.children[i].id);
    if (callee->kind == ExpressionKind::type) call.kind = CallKind::conversion;
    else if (callee->kind == ExpressionKind::member) {
      call.target = callee->children.at(0).id;
      if (call.name == "call") call.kind = CallKind::low_level;
      else if (call.name == "transfer") call.kind = CallKind::transfer;
      else if (call.name == "send") call.kind = CallKind::send;
      else if (call.name == "delegatecall") call.kind = CallKind::delegatecall;
      else if (call.name == "staticcall") call.kind = CallKind::staticcall;
      else call.kind = CallKind::external_member;
      if ((call.kind == CallKind::transfer || call.kind == CallKind::send) && !call.arguments.empty())
        call.value = call.arguments.front();
      note(call.id, call.location, "Member call classification is syntactic; receiver type and target are unresolved");
    } else if (callee->kind == ExpressionKind::identifier && !lookup(call.name) && !function_names_.contains(call.name) &&
               (call.name == "require" || call.name == "assert" || call.name == "revert" || call.name == "selfdestruct")) {
      call.kind = CallKind::builtin;
    } else {
      call.kind = function_names_.contains(call.name) && !lookup(call.name) ? CallKind::internal : CallKind::unknown;
      call.resolution = Resolution::unresolved;
      note(call.id, call.location, "Callee resolution and interprocedural effects are not implemented");
    }
    s.calls.push_back(std::move(call));
  }

  // One access for the full path (balances[key]), not another for its base balances.
  void collect_access(const Expression& e, Statement& s, AccessKind action, bool inspect_path = true) {
    const Expression* base = &e;
    std::vector<IrId> keys;
    while ((base->kind == ExpressionKind::index || base->kind == ExpressionKind::member) && !base->children.empty()) {
      if (base->kind == ExpressionKind::index && base->children.size() > 1) {
        keys.push_back(base->children[1].id);
        if (inspect_path) collect_facts(base->children[1], s);
      }
      base = &base->children[0];
    }
    if (base->kind != ExpressionKind::identifier) {
      if (inspect_path) collect_facts(*base, s);
      return;
    }
    const auto binding = lookup(base->name);
    if (!binding || binding->kind != VariableKind::state) return;
    std::reverse(keys.begin(), keys.end());
    s.state_accesses.push_back({next_id_++, binding->id, e.id, s.id, function_id_, action, keys, e.location});
  }

  void collect_facts(const Expression& e, Statement& s) {
    if (e.kind == ExpressionKind::assignment) {
      const auto& lhs = e.children.at(0);
      if (lhs.kind == ExpressionKind::tuple) {
        note(e.id, e.location, "Tuple assignment storage effects are unsupported");
      } else {
        if (e.op != "=") collect_access(lhs, s, AccessKind::read);
        collect_access(lhs, s, AccessKind::write, e.op == "=");
      }
      collect_facts(e.children.at(1), s);
      return;
    }
    if (e.kind == ExpressionKind::unary && (e.op == "++" || e.op == "--" || e.op == "delete")) {
      if (e.op != "delete") collect_access(e.children.at(0), s, AccessKind::read);
      collect_access(e.children.at(0), s, AccessKind::write, e.op == "delete");
      return;
    }
    if (e.kind == ExpressionKind::identifier || e.kind == ExpressionKind::index || e.kind == ExpressionKind::member) {
      collect_access(e, s, AccessKind::read);
      return;
    }
    if (e.kind == ExpressionKind::call) collect_call(e, s);
    for (const auto& child : e.children) collect_facts(child, s);
  }

  Statement statement(const json& node, IrId parent) {
    Statement s;
    s.id = next_id_++; s.parent = parent; s.function = function_id_; s.location = location(node);
    const auto type = node.value("nodeType", "");
    auto add_expression = [&](const char* field) {
      if (node.contains(field) && node.at(field).is_object()) {
        s.expressions.push_back(expression(node.at(field)));
        collect_facts(s.expressions.back(), s);
      }
    };
    if (type == "Block" || type == "UncheckedBlock") {
      s.kind = StatementKind::block;
      s.unchecked = type == "UncheckedBlock";
      scopes_.emplace_back();
      for (const auto& item : node.at("statements")) s.statements.push_back(statement(item, s.id));
      scopes_.pop_back();
    } else if (type == "IfStatement") {
      s.kind = StatementKind::branch; add_expression("condition");
      s.predicate = s.expressions.at(0).id;
      scopes_.emplace_back(); s.then_body.push_back(statement(node.at("trueBody"), s.id)); scopes_.pop_back();
      if (node.contains("falseBody") && node.at("falseBody").is_object()) {
        scopes_.emplace_back(); s.else_body.push_back(statement(node.at("falseBody"), s.id)); scopes_.pop_back();
      }
    } else if (type == "ExpressionStatement") {
      s.kind = StatementKind::expression; add_expression("expression");
      const auto& e = s.expressions.at(0);
      if (e.kind == ExpressionKind::call && !s.calls.empty() && s.calls.front().kind == CallKind::builtin) {
        const auto& name = s.calls.front().name;
        if ((name == "require" || name == "assert") && e.children.size() > 1) {
          s.kind = name == "require" ? StatementKind::require_guard : StatementKind::assert_guard;
          s.predicate = e.children[1].id;
        } else if (name == "revert") s.kind = StatementKind::revert_statement;
      }
    } else if (type == "VariableDeclarationStatement") {
      s.kind = StatementKind::declaration;
      add_expression("initialValue"); // Initializer sees the enclosing scope.
      for (const auto& decl : node.at("declarations"))
        if (decl.is_object()) s.declarations.push_back(variable(decl, VariableKind::local));
    } else if (type == "Return") {
      s.kind = StatementKind::return_statement; add_expression("expression");
    } else if (type == "RevertStatement") {
      s.kind = StatementKind::revert_statement; add_expression("errorCall");
    } else if (type == "EmitStatement") {
      s.kind = StatementKind::emit; add_expression("eventCall");
    } else {
      note(s.id, s.location, "Unsupported statement: " + type + "; body/effects were not analyzed");
    }
    if (s.calls.size() + s.state_accesses.size() > 1) {
      s.evaluation_order_known = false;
      note(s.id, s.location, "Subexpression execution order is unresolved; do not order effects by vector position");
    }
    return s;
  }

  Contract contract(const json& node) {
    Contract c;
    c.id = next_id_++; c.name = node.value("name", ""); c.kind = node.value("contractKind", "contract");
    c.location = location(node);
    scopes_.clear(); scopes_.emplace_back(); function_names_.clear();
    if (node.contains("baseContracts") && !node.at("baseContracts").empty())
      note(c.id, c.location, "Inherited declarations and behavior are unresolved");
    for (const auto& item : node.at("nodes")) {
      const auto type = item.value("nodeType", "");
      if (type == "VariableDeclaration") {
        c.variables.push_back(variable(item, VariableKind::state));
        if (item.contains("value") && !item.at("value").is_null())
          note(c.variables.back().id, location(item), "State initializer effects are not analyzed");
      } else if (type == "FunctionDefinition") function_names_[item.value("name", "")] = true;
      else note(c.id, location(item), "Contract member " + type + " is not expanded");
    }
    for (const auto& item : node.at("nodes")) {
      if (item.value("nodeType", "") != "FunctionDefinition") continue;
      Function f;
      f.id = next_id_++; function_id_ = f.id; f.contract = c.id;
      f.name = item.value("name", "");
      if (f.name.empty()) f.name = item.value("kind", "function");
      f.visibility = item.value("visibility", ""); f.mutability = item.value("stateMutability", "");
      f.location = location(item);
      scopes_.emplace_back();
      if (item.contains("parameters"))
        for (const auto& p : item.at("parameters").at("parameters")) f.parameters.push_back(variable(p, VariableKind::parameter));
      if (item.contains("returnParameters"))
        for (const auto& p : item.at("returnParameters").at("parameters")) f.returns.push_back(variable(p, VariableKind::return_value));
      if (item.contains("modifiers") && !item.at("modifiers").empty()) {
        note(f.id, f.location, "Modifier applications are not expanded; function reachability is unresolved");
        for (const auto& modifier : item.at("modifiers")) {
          ModifierApplication application;
          application.id = next_id_++;
          application.name = modifier.at("modifierName").value("name", "");
          application.location = location(modifier);
          if (modifier.contains("arguments") && modifier.at("arguments").is_array())
            for (const auto& argument : modifier.at("arguments"))
              application.arguments.push_back(expression(argument));
          f.modifiers.push_back(std::move(application));
        }
      }
      if (item.contains("body") && item.at("body").is_object()) f.body = statement(item.at("body"), no_id);
      scopes_.pop_back(); c.functions.push_back(std::move(f));
    }
    return c;
  }
};
} // namespace

Program build_ir(const nlohmann::json& output, const std::string& source, const std::string& file) {
  return Builder(source, file).build(output);
}
} // namespace smartshield
