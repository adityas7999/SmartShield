#include "smartshield/analyzer.hpp"
#include "smartshield/reentrancy_detector.hpp"
#include "smartshield/ir_builder.hpp"

namespace smartshield {
namespace {
using json = nlohmann::json;

const Expression* find_expression(const Expression& e, IrId id) {
  if (e.id == id) return &e;
  for (const auto& child : e.children)
    if (const auto* found = find_expression(child, id)) return found;
  return nullptr;
}

const Expression* find_origin(const Expression& e) {
  if (e.kind == ExpressionKind::builtin && e.name == "tx.origin") return &e;
  for (const auto& child : e.children)
    if (const auto* found = find_origin(child)) return found;
  return nullptr;
}

bool authorization_comparison(const Expression& e) {
  if (e.kind == ExpressionKind::binary && (e.op == "==" || e.op == "!=") && find_origin(e))
    return true;
  for (const auto& child : e.children)
    if (authorization_comparison(child)) return true;
  return false;
}

bool flow_boundary(const Statement& s) {
  return s.kind == StatementKind::return_statement ||
         s.kind == StatementKind::revert_statement ||
         s.kind == StatementKind::unsupported ||
         s.kind == StatementKind::branch || s.kind == StatementKind::block;
}

std::optional<std::string> sensitive_effect(const Statement& s) {
  for (const auto& call : s.calls) {
    if (call.kind == CallKind::transfer || call.kind == CallKind::send)
      return call.name;
    if (call.kind == CallKind::low_level && call.value) return ".call{value: ...}";
    if (call.kind == CallKind::builtin && call.name == "selfdestruct") return call.name;
  }
  return std::nullopt;
}

// Only inspect a straight-line suffix. Branches, exits and unknown flow stop the scan.
// This is a structural confidence heuristic, not a CFG or a reachability proof.
std::optional<std::string> following_effect(const std::vector<Statement>& statements,
                                           std::size_t first) {
  for (std::size_t i = first; i < statements.size(); ++i) {
    if (flow_boundary(statements[i])) break;
    if (auto effect = sensitive_effect(statements[i])) return effect;
  }
  return std::nullopt;
}

void collect_guards(const Statement& s, const Contract& contract, const Function& function,
                    std::optional<std::string> following, std::vector<GuardFact>& facts) {
  if (s.predicate != no_id) {
    const Expression* condition = nullptr;
    for (const auto& expression : s.expressions)
      if (const auto* found = find_expression(expression, s.predicate)) condition = found;
    if (condition && authorization_comparison(*condition)) {
      auto effect = following;
      std::string kind = s.kind == StatementKind::assert_guard ? "assert" : "require";
      if (s.kind == StatementKind::branch) {
        kind = "if";
        effect = std::nullopt;
        if (!s.then_body.empty()) {
          const auto& body = s.then_body.front();
          effect = body.kind == StatementKind::block
                       ? following_effect(body.statements, 0) : sensitive_effect(body);
        }
      }
      facts.push_back({kind, condition->text, contract.name, function.name,
                       find_origin(*condition)->location, effect});
    }
  }
  for (std::size_t i = 0; i < s.statements.size(); ++i)
    collect_guards(s.statements[i], contract, function,
                   following_effect(s.statements, i + 1), facts);
  for (const auto& child : s.then_body)
    collect_guards(child, contract, function, std::nullopt, facts);
  for (const auto& child : s.else_body)
    collect_guards(child, contract, function, std::nullopt, facts);
}

json location_json(const SourceLocation& location) {
  return {
      {"file", location.file},
      {"line", location.line},
      {"column", location.column},
      {"available", location.available},
  };
}

json finding_json(const GuardFact& fact) {
  const bool high_confidence = fact.sensitive_effect.has_value();
  std::vector<std::string> evidence{
      "Authorization condition contains tx.origin",
      fact.statement_type + " condition directly compares tx.origin",
  };
  std::vector<std::string> limitations{
      "Potential vulnerability only. Call classification and guard/effect association are syntactic; "
      "reachability, condition truth values, and exploitability are not proven."};

  if (high_confidence) {
    evidence.push_back("A syntactically guarded value-transfer call appears via " + *fact.sensitive_effect);
  } else {
    limitations.push_back(
        "No directly guarded sensitive effect was resolved in the same function; "
        "confidence is limited to the authorization-like guard.");
  }

  return {
      {"detectorId", "TXO-001"},
      {"vulnerabilityType", "tx.origin authorization misuse"},
      {"severity", "high"},
      {"confidence", high_confidence ? "high" : "medium"},
      {"location", location_json(fact.location)},
      {"contract", fact.contract_name},
      {"function", fact.function_name},
      {"explanation",
       high_confidence
           ? "tx.origin is used in an authorization-like guard associated with a potential value transfer."
           : "tx.origin is used in an authorization-like guard; no directly guarded sensitive effect was resolved."},
      {"evidence", evidence},
      {"limitations", limitations},
      {"irFacts",
       {
           {"statementType", fact.statement_type},
           {"conditionExpression", fact.condition},
           {"functionScope", fact.function_name},
           {"contractScope", fact.contract_name},
           {"guardClassification", "authorization_guard"},
           {"sensitiveEffect", fact.sensitive_effect.value_or("unresolved")},
       }},
  };
}

}  // namespace

nlohmann::json Analyzer::analyze(const nlohmann::json& compiler_output,
                                 const std::string& source,
                                 const std::string& file_name) const {
  const auto program = build_ir(compiler_output, source, file_name);
  std::vector<GuardFact> facts;
  const auto contract_count = program.contracts.size();
  std::size_t function_count = 0;
  for (const auto& contract : program.contracts) {
    function_count += contract.functions.size();
    for (const auto& function : contract.functions)
      if (function.body) collect_guards(*function.body, contract, function, std::nullopt, facts);
  }

  json findings = json::array();
  for (const auto& finding : ReentrancyDetector().detect(program)) findings.push_back(finding);
  for (const auto& fact : facts) {
    findings.push_back(finding_json(fact));
  }

  std::vector<std::string> analysis_limitations{
      "v0.1 analyzes direct require, assert, and if guards within one function.",
      "The solc parsing-only AST is not type-checked; declaration links are lexical and member-call kinds are syntactic.",
      "Modifiers, internal-call propagation, proxies, and full CFG/call-graph analysis are deferred.",
  };
  for (const auto& limitation : program.limitations)
    analysis_limitations.push_back(limitation.message);
  if (findings.empty()) {
    analysis_limitations.push_back(
        "No TXO-001 finding does not prove that the contract is secure.");
  }

  return {
      {"status", "completed"},
      {"findings", findings},
      {"analysisLimitations", analysis_limitations},
      {"analysisStages",
       {
           {{"id", "source"}, {"label", "Source received"}, {"status", "completed"}},
           {{"id", "parsed"}, {"label", "Parsed by solc"}, {"status", "completed"}},
           {{"id", "ir"}, {"label", "IR facts extracted"}, {"status", "completed"}},
           {{"id", "rule"}, {"label", "TXO-001 checked"}, {"status", "completed"}},
           {{"id", "reentrancy-rule"}, {"label", "REN-001 checked"}, {"status", "completed"}},
           {{"id", "result"},
            {"label", findings.empty() ? "No finding reported" : "Finding reported"},
            {"status", "completed"}},
       }},
      {"analysisSummary",
       {
           {"contractsInspected", contract_count},
           {"functionsInspected", function_count},
           {"authorizationGuards", static_cast<int>(facts.size())},
       }},
  };
}

}  // namespace smartshield
