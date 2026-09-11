#include "smartshield/reentrancy_detector.hpp"

#include <optional>
#include <string>
#include <vector>

namespace smartshield {
namespace {
using json = nlohmann::json;

json location_json(const SourceLocation& location) {
  return {
      {"file", location.file},
      {"line", location.line},
      {"column", location.column},
      {"available", location.available},
  };
}

const Expression* find_expression(const Expression& expression, IrId id) {
  if (expression.id == id) return &expression;
  for (const auto& child : expression.children)
    if (const auto* found = find_expression(child, id)) return found;
  return nullptr;
}

const Expression* find_expression(const Statement& statement, IrId id) {
  for (const auto& expression : statement.expressions)
    if (const auto* found = find_expression(expression, id)) return found;
  for (const auto& child : statement.statements)
    if (const auto* found = find_expression(child, id)) return found;
  for (const auto& child : statement.then_body)
    if (const auto* found = find_expression(child, id)) return found;
  for (const auto& child : statement.else_body)
    if (const auto* found = find_expression(child, id)) return found;
  return nullptr;
}

std::string key_text(const Statement& statement, IrId id, bool& resolved) {
  const auto* key = find_expression(statement, id);
  if (!key || !key->location.available || key->text.empty()) {
    resolved = false;
    return {};
  }
  return key->text;
}

bool same_storage(const StateAccess& before, const StateAccess& after,
                  const Statement& before_statement,
                  const Statement& after_statement, bool& resolved) {
  if (before.variable != after.variable || before.keys.size() != after.keys.size()) return false;
  for (std::size_t index = 0; index < before.keys.size(); ++index) {
    const auto before_key = key_text(before_statement, before.keys[index], resolved);
    const auto after_key = key_text(after_statement, after.keys[index], resolved);
    if (!resolved) return false;
    if (before_key != after_key) {
      resolved = false;
      return false;
    }
  }
  return true;
}

bool external_interaction(const Call& call) {
  switch (call.kind) {
    case CallKind::external_member:
    case CallKind::low_level:
    case CallKind::transfer:
    case CallKind::send:
    case CallKind::delegatecall:
    case CallKind::unknown:
      return true;
    default:
      return false;
  }
}

void flatten(const Statement& statement, std::vector<const Statement*>& result,
             bool& unsupported_control_flow) {
  if (statement.kind == StatementKind::block) {
    for (const auto& child : statement.statements) flatten(child, result, unsupported_control_flow);
    return;
  }
  if (statement.kind == StatementKind::branch) {
    unsupported_control_flow = true;
    return;
  }
  result.push_back(&statement);
}

json finding(const Contract& contract, const Function& function,
             const StateAccess& before, const Call& call, const StateAccess& after,
             bool unresolved_key, bool has_modifier) {
  std::vector<std::string> limitations{
      "Potential vulnerability only; exploitability is not proven.",
      "CFG facts are unavailable in this branch, so this direct result uses only a straight-line IR body.",
  };
  if (unresolved_key)
    limitations.push_back("The pre-call and post-call storage keys could not be proven equivalent.");
  if (has_modifier)
    limitations.push_back("Function modifiers are unresolved; an effective reentrancy guard was not proven.");

  json evidence = json::array({
      {{"kind", "state-read"},
       {"description", "A state location is read or checked before the external interaction."},
       {"location", location_json(before.location)}},
      {{"kind", "external-interaction"},
       {"description", "Control may leave the contract through an external interaction."},
       {"location", location_json(call.location)}},
      {{"kind", "state-write"},
       {"description", "The same state location is written after the external interaction."},
       {"location", location_json(after.location)}},
  });
  if (unresolved_key) {
    evidence.push_back({{"kind", "limitation"},
                        {"description", "Storage-key equivalence is unresolved; confidence is reduced."},
                        {"location", location_json(after.location)}});
  }

  return {
      {"detectorId", "REN-001"},
      {"vulnerabilityType", "reentrancy"},
      {"severity", "high"},
      {"confidence", unresolved_key || has_modifier ? "medium" : "high"},
      {"location", location_json(call.location)},
      {"contract", contract.name},
      {"function", function.name},
      {"explanation", "Potential reentrancy: a reachable direct state check precedes an external interaction and a matching state write follows it."},
      {"evidence", evidence},
      {"limitations", limitations},
  };
}

}  // namespace

nlohmann::json ReentrancyDetector::detect(const Program& program) const {
  json findings = json::array();
  for (const auto& contract : program.contracts) {
    for (const auto& function : contract.functions) {
      if (!function.body) continue;
      std::vector<const Statement*> statements;
      bool unsupported_control_flow = false;
      flatten(*function.body, statements, unsupported_control_flow);
      for (std::size_t call_index = 0; call_index < statements.size(); ++call_index) {
        const auto& call_statement = *statements[call_index];
        if (!call_statement.evaluation_order_known) continue;
        for (const auto& call : call_statement.calls) {
          if (!external_interaction(call)) continue;
          for (std::size_t before_index = 0; before_index < call_index; ++before_index) {
            for (const auto& before : statements[before_index]->state_accesses) {
              if (before.action != AccessKind::read) continue;
              for (std::size_t after_index = call_index + 1; after_index < statements.size(); ++after_index) {
                for (const auto& after : statements[after_index]->state_accesses) {
                  if (after.action != AccessKind::write) continue;
                  bool keys_resolved = true;
                  if (same_storage(before, after, *statements[before_index],
                                   *statements[after_index], keys_resolved)) {
                    findings.push_back(finding(contract, function, before, call, after,
                                               !keys_resolved, !function.modifiers.empty()));
                    goto next_function;
                  }
                  if (!keys_resolved && before.variable == after.variable) {
                    findings.push_back(finding(contract, function, before, call, after,
                                               true, !function.modifiers.empty()));
                    goto next_function;
                  }
                }
              }
            }
          }
        }
      }
      if (unsupported_control_flow) {
        continue;
      }
    next_function:;
    }
  }
  return findings;
}

}  // namespace smartshield