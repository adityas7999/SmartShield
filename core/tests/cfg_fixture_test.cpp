#include "smartshield/cfg.hpp"
#include "smartshield/ir_builder.hpp"

#include <iostream>
#include <nlohmann/json.hpp>
#include <stdexcept>

using namespace smartshield;
using json = nlohmann::json;

namespace {
void expect(bool value, const std::string& message) { if (!value) throw std::runtime_error(message); }
const Function& find_function(const Program& program, const std::string& name) {
  for (const auto& contract : program.contracts) for (const auto& function : contract.functions)
    if (function.name == name) return function;
  throw std::runtime_error("function not found: " + name);
}
void collect(const Statement& statement, std::vector<const Statement*>& result) {
  result.push_back(&statement);
  for (const auto& child : statement.statements) collect(child, result);
  for (const auto& child : statement.then_body) collect(child, result);
  for (const auto& child : statement.else_body) collect(child, result);
}
}

int main() {
  try {
    json request; std::cin >> request;
    const auto source = request.at("source").get<std::string>();
    const auto file = request.at("fileName").get<std::string>();
    const auto program = build_ir(request.at("compilerOutput"), source, file);
    const auto& function = find_function(program, request.value("function", "withdraw"));
    const auto graph = build_cfg(function, program.limitations);
    expect(graph.available, "fixture function must have a body");
    expect(graph.entry != graph.normal_exit && graph.entry != graph.exceptional_exit, "synthetic IDs must be distinct");

    std::vector<const Statement*> statements;
    collect(*function.body, statements);
    std::vector<GraphNodeId> call_nodes;
    std::vector<GraphNodeId> read_nodes;
    std::vector<GraphNodeId> write_nodes;
    GraphNodeId guard_node = 0;
    for (const auto* statement : statements) {
      const auto nodes = graph.nodes_for_statement(statement->id);
      if (nodes.empty()) continue;
      if (statement->kind == StatementKind::require_guard || statement->kind == StatementKind::assert_guard) guard_node = nodes.front();
      for (const auto& call : statement->calls)
        if (call.kind == CallKind::transfer || call.kind == CallKind::send || call.kind == CallKind::low_level) call_nodes.push_back(nodes.front());
      for (const auto& access : statement->state_accesses) {
        if (access.action == AccessKind::read) read_nodes.push_back(nodes.front());
        if (access.action == AccessKind::write) write_nodes.push_back(nodes.front());
      }
    }
    const auto scenario = request.value("scenario", "");
    if (scenario == "guard") {
      expect(guard_node && !call_nodes.empty(), "guard fixture facts missing");
      expect(graph.ordered(guard_node, call_nodes.front()).is_yes(), "guard success must reach call");
      expect(graph.branch_reachable(guard_node, CfgEdgeKind::false_branch, graph.exceptional_exit).is_yes(), "guard failure must revert");
    } else if (scenario == "effects") {
      expect(!read_nodes.empty() && !call_nodes.empty() && !write_nodes.empty(), "effect fixture facts missing");
      expect(graph.ordered({read_nodes.front(), call_nodes.front(), write_nodes.front()}).is_yes(), "check/call/write order missing");
    } else if (scenario == "checks_effects") {
      expect(!call_nodes.empty() && !write_nodes.empty(), "checks-effects facts missing");
      expect(graph.ordered(write_nodes.front(), call_nodes.front()).is_yes(), "write must precede call");
      expect(graph.ordered(call_nodes.front(), write_nodes.front()).status == QueryStatus::no, "call must not precede write");
    }
    if (request.value("expectModifierUncertainty", false)) expect(!graph.complete && !graph.modifiers.empty(), "modifier uncertainty missing");

    json result{{"available", graph.available}, {"complete", graph.complete}, {"nodes", graph.nodes.size()}, {"edges", graph.edges.size()}, {"modifiers", graph.modifiers.size()}};
    std::cout << result << '\n';
    return 0;
  } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}