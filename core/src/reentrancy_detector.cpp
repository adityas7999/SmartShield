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

enum class StorageRelation { same, different, unresolved };

StorageRelation expression_relation(const Expression* before, const Expression* after) {
  if (!before || !after) return StorageRelation::unresolved;
  if (before->kind == ExpressionKind::call || before->kind == ExpressionKind::call_options ||
      before->kind == ExpressionKind::unknown || after->kind == ExpressionKind::call ||
      after->kind == ExpressionKind::call_options || after->kind == ExpressionKind::unknown ||
      before->resolution == Resolution::unresolved || after->resolution == Resolution::unresolved)
    return StorageRelation::unresolved;
  if (before->kind != after->kind) return StorageRelation::different;
  switch (before->kind) {
    case ExpressionKind::literal:
      return before->name == after->name ? StorageRelation::same : StorageRelation::different;
    case ExpressionKind::builtin:
      return before->name == after->name ? StorageRelation::same : StorageRelation::different;
    case ExpressionKind::identifier:
      if (before->variable == no_id || after->variable == no_id)
        return StorageRelation::unresolved;
      return before->variable == after->variable ? StorageRelation::same : StorageRelation::different;
    default:
      break;
  }
  if (before->name != after->name || before->op != after->op ||
      before->children.size() != after->children.size())
    return StorageRelation::different;
  StorageRelation result = StorageRelation::same;
  for (std::size_t index = 0; index < before->children.size(); ++index) {
    const auto child = expression_relation(&before->children[index], &after->children[index]);
    if (child == StorageRelation::different) return child;
    if (child == StorageRelation::unresolved) result = child;
  }
  return result;
}

StorageRelation storage_relation(const StateAccess& before, const StateAccess& after,
                                 const Statement& before_statement,
                                 const Statement& after_statement) {
  if (before.variable != after.variable || before.keys.size() != after.keys.size())
    return StorageRelation::different;
  StorageRelation result = StorageRelation::same;
  for (std::size_t index = 0; index < before.keys.size(); ++index) {
    const auto relation = expression_relation(find_expression(before_statement, before.keys[index]),
                                              find_expression(after_statement, after.keys[index]));
    if (relation == StorageRelation::different) return relation;
    if (relation == StorageRelation::unresolved) result = relation;
  }
  return result;
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

void direct_sequences(const Statement& body, std::vector<std::vector<const Statement*>>& sequences,
                      std::vector<std::string>& limitations) {
  if (body.kind != StatementKind::block) {
    limitations.push_back("Function body is not a directly ordered block; REN-001 was not evaluated.");
    return;
  }
  std::vector<const Statement*> current;
  for (const auto& child : body.statements) {
    const bool boundary = child.kind == StatementKind::branch || child.kind == StatementKind::block ||
                          child.kind == StatementKind::return_statement ||
                          child.kind == StatementKind::revert_statement ||
                          child.kind == StatementKind::unsupported;
    if (boundary) {
      if (!current.empty()) sequences.push_back(std::move(current));
      current.clear();
      limitations.push_back("Control-flow boundaries are unresolved; REN-001 does not claim a path across this statement.");
      continue;
    }
    current.push_back(&child);
  }
  if (!current.empty()) sequences.push_back(std::move(current));
}

json finding(const Contract& contract, const Function& function,
             const StateAccess& before, const Call& call, const StateAccess& after,
             bool unresolved_key, bool has_modifier, bool unknown_order, bool unknown_call) {
  std::vector<std::string> limitations{
      "Potential vulnerability only; exploitability is not proven.",
      "CFG facts are unavailable in this branch, so this direct result uses only a straight-line IR body.",
  };
  if (unresolved_key)
    limitations.push_back("The pre-call and post-call storage keys could not be proven equivalent.");
  if (has_modifier)
    limitations.push_back("Function modifiers are unresolved; an effective reentrancy guard was not proven.");

  const std::vector<std::string> evidence{
      "State location is read before the external interaction.",
      "Control may leave the contract through an external interaction.",
      "The same state location is written after the external interaction.",
  };
  json evidence_details = json::array({
      {{"kind", "state-read"}, {"description", evidence[0]}, {"location", location_json(before.location)}},
      {{"kind", "external-interaction"}, {"description", evidence[1]}, {"location", location_json(call.location)}},
      {{"kind", "state-write"}, {"description", evidence[2]}, {"location", location_json(after.location)}},
  });
  if (unresolved_key) {
    limitations.push_back("Storage-key equivalence is unresolved; confidence is reduced.");
    evidence_details.push_back({{"kind", "limitation"},
                                {"description", "Storage-key equivalence is unresolved; confidence is reduced."},
                                {"location", location_json(after.location)}});
  }
  if (unknown_order)
    limitations.push_back("The external-call statement contains additional effects whose internal order is unresolved.");
  if (unknown_call)
    limitations.push_back("The external interaction is syntactically classified but its call target is unresolved.");

  return {
      {"detectorId", "REN-001"},
      {"vulnerabilityType", "reentrancy"},
      {"severity", "high"},
      {"confidence", unresolved_key || has_modifier || unknown_order || unknown_call ? "medium" : "high"},
      {"location", location_json(call.location)},
      {"contract", contract.name},
      {"function", function.name},
      {"explanation", "Potential reentrancy: the supported straight-line IR sequence contains a state read before an external interaction and a matching state write after it."},
      {"evidence", evidence},
      {"evidenceDetails", evidence_details},
      {"limitations", limitations},
  };
}

}  // namespace

nlohmann::json ReentrancyDetector::detect(const Program& program) const {
  return analyze(program).findings;
}

ReentrancyAnalysis ReentrancyDetector::analyze(const Program& program) const {
  json findings = json::array();
  std::vector<std::string> limitations;
  for (const auto& contract : program.contracts) {
    for (const auto& function : contract.functions) {
      if (!function.body) continue;
      std::vector<std::vector<const Statement*>> sequences;
      direct_sequences(*function.body, sequences, limitations);
      if (!function.modifiers.empty())
        limitations.push_back("Function modifiers are unresolved; REN-001 does not claim that a guard is absent.");
      for (const auto& statements : sequences) {
       for (std::size_t call_index = 0; call_index < statements.size(); ++call_index) {
        const auto& call_statement = *statements[call_index];
        for (const auto& call : call_statement.calls) {
          if (!external_interaction(call)) continue;
          bool candidate_found = false;
          for (std::size_t before_index = 0; before_index < call_index; ++before_index) {
            for (const auto& before : statements[before_index]->state_accesses) {
              if (before.action != AccessKind::read) continue;
              for (std::size_t after_index = call_index + 1; after_index < statements.size(); ++after_index) {
                for (const auto& after : statements[after_index]->state_accesses) {
                  if (after.action != AccessKind::write) continue;
                  const auto relation = storage_relation(before, after, *statements[before_index],
                                                         *statements[after_index]);
                  if (relation == StorageRelation::same || relation == StorageRelation::unresolved) {
                    findings.push_back(finding(contract, function, before, call, after,
                                               relation == StorageRelation::unresolved,
                                               !function.modifiers.empty(),
                                               !call_statement.evaluation_order_known,
                                               call.kind == CallKind::unknown));
                    candidate_found = true;
                    break;
                  }
                }
                if (candidate_found) break;
              }
              if (candidate_found) break;
            }
            if (candidate_found) break;
          }
        }
       }
      }
    }
  }
  return {findings, limitations};
}

}  // namespace smartshield