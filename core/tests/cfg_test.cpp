#include "smartshield/cfg.hpp"

#include <iostream>
#include <stdexcept>

using namespace smartshield;

namespace {
void expect(bool value, const char* message) { if (!value) throw std::runtime_error(message); }

Statement statement(IrId id, StatementKind kind = StatementKind::expression) {
  Statement result; result.id = id; result.function = 1; result.kind = kind; return result;
}
Statement block(IrId id, std::vector<Statement> children) {
  auto result = statement(id, StatementKind::block); result.statements = std::move(children);
  for (auto& child : result.statements) child.parent = id;
  return result;
}
Statement guard(IrId id, bool value, StatementKind kind = StatementKind::require_guard) {
  auto result = statement(id, kind); result.predicate = id + 100;
  Expression predicate; predicate.id = id + 100; predicate.kind = ExpressionKind::literal;
  predicate.name = value ? "true" : "false"; result.expressions.push_back(predicate); return result;
}
Statement branch(IrId id, std::vector<Statement> yes, std::vector<Statement> no = {}) {
  auto result = statement(id, StatementKind::branch); result.predicate = id + 100;
  Expression predicate; predicate.id = id + 100; predicate.kind = ExpressionKind::identifier;
  predicate.name = "flag"; result.expressions.push_back(predicate);
  result.then_body = std::move(yes); result.else_body = std::move(no);
  for (auto& child : result.then_body) child.parent = id;
  for (auto& child : result.else_body) child.parent = id;
  return result;
}
Function function(std::vector<Statement> children) {
  Function result; result.id = 1; result.contract = 2; result.name = "f";
  result.body = block(10, std::move(children)); return result;
}
GraphNodeId only(const CfgGraph& graph, IrId statement_id) {
  const auto nodes = graph.nodes_for_statement(statement_id);
  expect(nodes.size() == 1, "expected one statement node");
  return nodes.front();
}
}

int main() {
  try {
    const auto empty = build_cfg(function({}));
    expect(empty.available && empty.edges.size() == 2, "empty body must connect entry through block to exit");
    expect(empty.reachable(empty.normal_exit).is_yes(), "empty body exit must be reachable");

    const auto straight = build_cfg(function({statement(1), statement(2), statement(3)}));
    expect(straight.ordered({only(straight, 1), only(straight, 2), only(straight, 3)}).is_yes(), "straight-line sequence");
    expect(straight.ordered(only(straight, 1), only(straight, 1)).status == QueryStatus::no, "same node is not strict order");
    expect(straight.nodes_for_statement(999).empty(), "missing mapping is empty");
    expect(straight.ordered(999, only(straight, 1)).status == QueryStatus::invalid, "invalid ID is invalid");
    auto other_function = function({statement(2)}); other_function.id = 2;
    const auto other_graph = build_cfg(other_function);
    expect(straight.ordered(other_graph.entry, straight.entry).status == QueryStatus::invalid, "cross-function ID is invalid");

    auto effects_statement = statement(4);
    effects_statement.evaluation_order_known = false;
    effects_statement.calls.push_back({5, 6, 4, 1, CallKind::low_level, Resolution::syntax_only, "call", 7, {}, {}, {}});
    effects_statement.state_accesses.push_back({8, 9, 10, 4, 1, AccessKind::write, {}, {}});
    const auto effects = build_cfg(function({effects_statement}));
    expect(effects.ordered_effects(5, 8).status == QueryStatus::unknown, "same-statement effect order is unknown");

    expect(effects.complete, "subexpression uncertainty must not hide statement flow");
    const auto before_after = build_cfg(function({statement(3), effects_statement}));
    expect(before_after.ordered(only(before_after, 3), only(before_after, 4)).is_yes(), "earlier statement precedes uncertain effects");
    expect(before_after.ordered(only(before_after, 4), only(before_after, 3)).status == QueryStatus::no, "uncertain effects cannot reverse statement order");
    expect(before_after.ordered({only(before_after, 4), only(before_after, 3), 999}).status == QueryStatus::invalid, "validate entire sequence before answering");

    const auto graph = build_cfg(function({branch(20, {statement(21, StatementKind::return_statement)}, {statement(22)}), statement(23)}));
    expect(graph.branch_reachable(only(graph, 20), CfgEdgeKind::true_branch, graph.normal_exit).is_yes(), "true return reaches normal exit");
    expect(graph.ordered(only(graph, 20), only(graph, 23)).is_yes(), "non-terminating branch reaches join");
    expect(graph.ordered(only(graph, 21), only(graph, 23)).status == QueryStatus::no, "return has no fall-through");

    expect(graph.branch_reachable(only(graph, 20), CfgEdgeKind::normal, graph.normal_exit).status == QueryStatus::invalid, "invalid branch selector");
    const auto dead_branch = build_cfg(function({statement(24, StatementKind::return_statement), branch(25, {statement(26)})}));
    expect(dead_branch.branch_reachable(only(dead_branch, 25), CfgEdgeKind::true_branch, only(dead_branch, 26)).status == QueryStatus::no, "unreachable branch cannot reach its body from entry");

    const auto both_terminate = build_cfg(function({branch(30, {statement(31, StatementKind::return_statement)}, {statement(32, StatementKind::revert_statement)}), statement(33)}));
    expect(both_terminate.reachable(only(both_terminate, 33)).status == QueryStatus::no, "both terminating branches leave join unreachable");

    const auto guard_graph = build_cfg(function({guard(40, true), statement(41)}));
    expect(guard_graph.branch_reachable(only(guard_graph, 40), CfgEdgeKind::false_branch, guard_graph.exceptional_exit).status == QueryStatus::no, "require(true) failure is infeasible");
    const auto false_guard = build_cfg(function({guard(50, false), statement(51)}));
    expect(false_guard.reachable(false_guard.exceptional_exit).is_yes(), "require(false) reverts");
    expect(false_guard.reachable(only(false_guard, 51)).status == QueryStatus::no, "require(false) has no normal continuation");

    const auto unsupported = build_cfg(function({statement(60, StatementKind::unsupported), statement(61)}));
    expect(!unsupported.complete && unsupported.reachable(only(unsupported, 61)).status == QueryStatus::unknown, "unsupported flow is unknown");

    auto modifier_function = function({statement(70)});
    modifier_function.modifiers.push_back({71, "nonReentrant", {}, {}, Resolution::unresolved});
    const auto modifiers = build_cfg(modifier_function);
    expect(!modifiers.complete && modifiers.modifiers.size() == 1, "modifier uncertainty is retained");

    Function declaration; declaration.id = 80; declaration.contract = 2; declaration.name = "decl";
    const auto unavailable = build_cfg(declaration);
    expect(!unavailable.available && unavailable.unavailable_reason.find("no executable body") != std::string::npos, "declaration is unavailable");

    const auto first = build_cfg(function({branch(90, {statement(91)}, {statement(92)}), statement(93)}));
    const auto second = build_cfg(function({branch(90, {statement(91)}, {statement(92)}), statement(93)}));
    expect(first.nodes.size() == second.nodes.size() && first.edges.size() == second.edges.size(), "graph construction is deterministic");
    std::cout << "CFG synthetic tests passed\n";
  } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}