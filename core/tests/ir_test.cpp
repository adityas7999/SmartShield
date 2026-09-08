#include "smartshield/ir_builder.hpp"
#include "smartshield/analyzer.hpp"

#include <iostream>
#include <stdexcept>
#include <unordered_set>
#include <nlohmann/json.hpp>

namespace {
using namespace smartshield;
using json = nlohmann::json;

void expect(bool value, const char* message) {
  if (!value) throw std::runtime_error(message);
}

// Test-only projection. Production consumers use the C++ model, not this JSON.
class Inspector {
 public:
  json inspect(const Program& program) {
    for (const auto& contract : program.contracts) {
      add(contract.id);
      for (const auto& variable : contract.variables) add(variable.id);
      for (const auto& function : contract.functions) {
        add(function.id);
        expect(function.contract == contract.id, "wrong function owner");
        for (const auto& variable : function.parameters) add(variable.id);
        for (const auto& variable : function.returns) add(variable.id);
        for (const auto& modifier : function.modifiers) {
          add(modifier.id);
          modifiers.push_back(modifier.name);
          for (const auto& argument : modifier.arguments) expression(argument);
        }
        if (function.body) statement(*function.body, no_id, function.id);
      }
    }
    for (const auto id : references) expect(ids.contains(id), "dangling IR reference");
    json limitations = json::array();
    for (const auto& limitation : program.limitations) {
      if (limitation.entity != no_id) expect(ids.contains(limitation.entity), "dangling limitation");
      limitations.push_back(limitation.message);
    }
    return {{"statements", statements}, {"expressions", expressions}, {"calls", calls},
            {"accesses", accesses}, {"modifiers", modifiers}, {"limitations", limitations}};
  }

 private:
  std::unordered_set<IrId> ids;
  std::vector<IrId> references;
  json statements = json::array(), expressions = json::array(), calls = json::array();
  json accesses = json::array(), modifiers = json::array();

  void add(IrId id) { expect(id != no_id && ids.insert(id).second, "zero or duplicate ID"); }
  void reference(IrId id) { expect(id != no_id, "missing required reference"); references.push_back(id); }

  void expression(const Expression& e) {
    add(e.id);
    if (e.variable != no_id) reference(e.variable);
    expressions.push_back({{"id", e.id}, {"name", e.name}, {"text", e.text},
                           {"variable", e.variable}, {"kind", static_cast<int>(e.kind)},
                           {"offset", e.location.offset}, {"line", e.location.line},
                           {"column", e.location.column}, {"available", e.location.available}});
    for (const auto& child : e.children) expression(child);
  }

  void statement(const Statement& s, IrId parent, IrId function) {
    add(s.id);
    expect(s.parent == parent && s.function == function, "wrong statement owner");
    for (const auto& declaration : s.declarations) add(declaration.id);
    for (const auto& e : s.expressions) expression(e);
    if (s.predicate != no_id) reference(s.predicate);
    statements.push_back({{"id", s.id}, {"parent", parent}, {"function", function},
                          {"kind", static_cast<int>(s.kind)}, {"predicate", s.predicate},
                          {"ordered", s.evaluation_order_known}, {"unchecked", s.unchecked},
                          {"thenCount", s.then_body.size()}, {"elseCount", s.else_body.size()}});
    for (const auto& call : s.calls) {
      add(call.id); reference(call.expression); reference(call.target);
      expect(call.statement == s.id && call.function == function, "wrong call owner");
      for (auto argument : call.arguments) reference(argument);
      if (call.value) reference(*call.value);
      calls.push_back({{"name", call.name}, {"statement", s.id},
                       {"kind", static_cast<int>(call.kind)}, {"arguments", call.arguments},
                       {"value", call.value.value_or(no_id)}});
    }
    for (const auto& access : s.state_accesses) {
      add(access.id); reference(access.variable); reference(access.expression);
      expect(access.statement == s.id && access.function == function, "wrong access owner");
      for (auto key : access.keys) reference(key);
      accesses.push_back({{"variable", access.variable}, {"expression", access.expression},
                         {"statement", s.id}, {"action", access.action == AccessKind::read ? "read" : "write"},
                         {"keys", access.keys}});
    }
    for (const auto& child : s.statements) statement(child, s.id, function);
    for (const auto& child : s.then_body) statement(child, s.id, function);
    for (const auto& child : s.else_body) statement(child, s.id, function);
  }
};
} // namespace

int main() {
  try {
    json request;
    std::cin >> request;
    const auto source = request.at("source").get<std::string>();
    const auto file = request.at("fileName").get<std::string>();
    const auto& output = request.at("compilerOutput");
    const auto first = Inspector().inspect(smartshield::build_ir(output, source, file));
    const auto second = Inspector().inspect(smartshield::build_ir(output, source, file));
    expect(first == second, "IR IDs/facts must be deterministic for identical input");
    json result = first;
    result["analysis"] = smartshield::Analyzer().analyze(output, source, file);
    std::cout << result << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
