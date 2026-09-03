#include "smartshield/analyzer.hpp"

#include <algorithm>
#include <sstream>
#include <stdexcept>
#include <string_view>

namespace smartshield {
namespace {

using json = nlohmann::json;

struct SourceRange {
  std::size_t offset{0};
  std::size_t length{0};
};

SourceRange parse_source_range(const json& node) {
  if (!node.contains("src") || !node["src"].is_string()) {
    return {};
  }

  const std::string src = node["src"].get<std::string>();
  const auto first = src.find(':');
  const auto second = first == std::string::npos ? std::string::npos : src.find(':', first + 1);
  if (first == std::string::npos || second == std::string::npos) {
    return {};
  }

  try {
    return {
        static_cast<std::size_t>(std::stoull(src.substr(0, first))),
        static_cast<std::size_t>(std::stoull(src.substr(first + 1, second - first - 1))),
    };
  } catch (const std::exception&) {
    return {};
  }
}

SourceLocation location_for(const json& node,
                            const std::string& source,
                            const std::string& file_name) {
  const auto range = parse_source_range(node);
  const auto safe_offset = std::min(range.offset, source.size());
  const auto last_newline = source.rfind('\n', safe_offset == 0 ? 0 : safe_offset - 1);

  SourceLocation location;
  location.file = file_name;
  location.offset = safe_offset;
  location.length = std::min(range.length, source.size() - safe_offset);
  location.line = static_cast<int>(std::count(source.begin(), source.begin() + safe_offset, '\n')) + 1;
  location.column = last_newline == std::string::npos
                        ? static_cast<int>(safe_offset) + 1
                        : static_cast<int>(safe_offset - last_newline);
  return location;
}

std::string source_text(const json& node, const std::string& source) {
  const auto range = parse_source_range(node);
  if (range.offset >= source.size()) {
    return {};
  }
  return source.substr(range.offset, std::min(range.length, source.size() - range.offset));
}

bool is_ast_node(const json& value) {
  return value.is_object() && value.contains("nodeType") && value["nodeType"].is_string();
}

template <typename Visitor>
void visit_children(const json& node, Visitor&& visitor) {
  if (!node.is_object()) {
    return;
  }
  for (auto it = node.begin(); it != node.end(); ++it) {
    const auto& value = it.value();
    if (is_ast_node(value)) {
      visitor(value);
    } else if (value.is_array()) {
      for (const auto& child : value) {
        if (is_ast_node(child)) {
          visitor(child);
        }
      }
    }
  }
}

bool is_tx_origin(const json& node) {
  if (node.value("nodeType", "") != "MemberAccess" || node.value("memberName", "") != "origin") {
    return false;
  }
  const auto expression = node.find("expression");
  return expression != node.end() && expression->is_object() &&
         expression->value("nodeType", "") == "Identifier" &&
         expression->value("name", "") == "tx";
}

const json* find_tx_origin(const json& node) {
  if (is_tx_origin(node)) {
    return &node;
  }

  const json* match = nullptr;
  visit_children(node, [&](const json& child) {
    if (match == nullptr) {
      match = find_tx_origin(child);
    }
  });
  return match;
}

bool is_authorization_comparison(const json& condition) {
  bool found = false;
  if (condition.value("nodeType", "") == "BinaryOperation") {
    const auto op = condition.value("operator", "");
    if ((op == "==" || op == "!=") && find_tx_origin(condition) != nullptr) {
      return true;
    }
  }
  visit_children(condition, [&](const json& child) {
    if (!found) {
      found = is_authorization_comparison(child);
    }
  });
  return found;
}

std::optional<std::string> sensitive_call_kind(const json& node) {
  if (node.value("nodeType", "") != "FunctionCall") {
    return std::nullopt;
  }

  const auto expression_it = node.find("expression");
  if (expression_it == node.end() || !expression_it->is_object()) {
    return std::nullopt;
  }

  const json* expression = &(*expression_it);
  if (expression->value("nodeType", "") == "FunctionCallOptions") {
    const auto nested = expression->find("expression");
    if (nested != expression->end() && nested->is_object()) {
      expression = &(*nested);
    }
  }

  if (expression->value("nodeType", "") == "MemberAccess") {
    const auto member = expression->value("memberName", "");
    if (member == "transfer" || member == "send" || member == "call" ||
        member == "delegatecall") {
      return member;
    }
  }

  const auto name = expression->value("name", "");
  if (name == "selfdestruct" || name == "suicide") {
    return name;
  }
  return std::nullopt;
}

std::optional<std::string> find_sensitive_effect(const json& node,
                                                 std::size_t after_offset = 0) {
  const auto range = parse_source_range(node);
  if (range.offset >= after_offset) {
    if (const auto call = sensitive_call_kind(node); call.has_value()) {
      return call;
    }
  }

  std::optional<std::string> match;
  visit_children(node, [&](const json& child) {
    if (!match.has_value()) {
      match = find_sensitive_effect(child, after_offset);
    }
  });
  return match;
}

std::string function_display_name(const json& function) {
  const auto name = function.value("name", "");
  if (!name.empty()) {
    return name;
  }
  return function.value("kind", "function");
}

void collect_guard_facts(const json& node,
                         const json& function_body,
                         const std::string& contract_name,
                         const std::string& function_name,
                         const std::string& source,
                         const std::string& file_name,
                         std::vector<GuardFact>& facts) {
  const auto node_type = node.value("nodeType", "");
  const json* condition = nullptr;
  std::string statement_type;
  std::optional<std::string> sensitive_effect;

  if (node_type == "IfStatement") {
    const auto it = node.find("condition");
    if (it != node.end() && it->is_object()) {
      condition = &(*it);
      statement_type = "if";
      const auto true_body = node.find("trueBody");
      if (true_body != node.end() && true_body->is_object()) {
        sensitive_effect = find_sensitive_effect(*true_body);
      }
    }
  } else if (node_type == "FunctionCall") {
    const auto expression = node.find("expression");
    const auto arguments = node.find("arguments");
    if (expression != node.end() && expression->is_object() &&
        expression->value("nodeType", "") == "Identifier" &&
        (expression->value("name", "") == "require" ||
         expression->value("name", "") == "assert") &&
        arguments != node.end() && arguments->is_array() && !arguments->empty() &&
        (*arguments)[0].is_object()) {
      condition = &(*arguments)[0];
      statement_type = expression->value("name", "guard");
      const auto guard_range = parse_source_range(node);
      sensitive_effect = find_sensitive_effect(function_body, guard_range.offset + guard_range.length);
    }
  }

  if (condition != nullptr && find_tx_origin(*condition) != nullptr &&
      is_authorization_comparison(*condition)) {
    const auto* origin = find_tx_origin(*condition);
    facts.push_back({
        statement_type,
        source_text(*condition, source),
        contract_name,
        function_name,
        location_for(*origin, source, file_name),
        sensitive_effect,
    });
    return;
  }

  visit_children(node, [&](const json& child) {
    collect_guard_facts(child, function_body, contract_name, function_name, source,
                        file_name, facts);
  });
}

void collect_function_facts(const json& node,
                            const std::string& contract_name,
                            const std::string& source,
                            const std::string& file_name,
                            std::vector<GuardFact>& facts,
                            int& function_count) {
  if (node.value("nodeType", "") == "FunctionDefinition") {
    ++function_count;
    const auto body = node.find("body");
    if (body != node.end() && body->is_object()) {
      collect_guard_facts(*body, *body, contract_name, function_display_name(node), source,
                          file_name, facts);
    }
    return;
  }

  visit_children(node, [&](const json& child) {
    collect_function_facts(child, contract_name, source, file_name, facts, function_count);
  });
}

json location_json(const SourceLocation& location) {
  return {
      {"file", location.file},
      {"line", location.line},
      {"column", location.column},
  };
}

json finding_json(const GuardFact& fact) {
  const bool high_confidence = fact.sensitive_effect.has_value();
  std::vector<std::string> evidence{
      "Authorization condition contains tx.origin",
      fact.statement_type + " condition directly compares tx.origin",
  };
  std::vector<std::string> limitations;

  if (high_confidence) {
    evidence.push_back("Guard controls a value transfer via " + *fact.sensitive_effect);
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
           ? "tx.origin is used in an authorization guard that controls a sensitive value transfer."
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
  const auto sources = compiler_output.find("sources");
  if (sources == compiler_output.end() || !sources->is_object() || sources->empty()) {
    throw std::runtime_error("Compiler output does not contain a sources object");
  }

  auto source_entry = sources->find(file_name);
  if (source_entry == sources->end()) {
    source_entry = sources->begin();
  }
  if (!source_entry->is_object() || !source_entry->contains("ast")) {
    throw std::runtime_error("Compiler output does not contain a source AST");
  }

  const auto& ast = (*source_entry)["ast"];
  std::vector<GuardFact> facts;
  int contract_count = 0;
  int function_count = 0;

  const auto nodes = ast.find("nodes");
  if (nodes != ast.end() && nodes->is_array()) {
    for (const auto& node : *nodes) {
      if (node.value("nodeType", "") != "ContractDefinition") {
        continue;
      }
      ++contract_count;
      collect_function_facts(node, node.value("name", "<anonymous>"), source, file_name,
                             facts, function_count);
    }
  }

  json findings = json::array();
  for (const auto& fact : facts) {
    findings.push_back(finding_json(fact));
  }

  std::vector<std::string> analysis_limitations{
      "v0.1 analyzes direct require, assert, and if guards within one function.",
      "Modifiers, internal-call propagation, proxies, and full CFG/call-graph analysis are deferred.",
  };
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
