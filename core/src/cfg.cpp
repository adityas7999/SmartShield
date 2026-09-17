#include "smartshield/cfg.hpp"

#include <algorithm>
#include <functional>
#include <queue>
#include <unordered_set>

namespace smartshield {
namespace {

struct Flow { GraphNodeId entry{0}; bool normal{true}; };

class Builder {
 public:
  Builder(const Function& function, const std::vector<Limitation>& limitations)
      : function_(function) {
    graph_.contract = function.contract;
    graph_.function = function.id;
    graph_.limitations = limitations;
    graph_.modifiers = function.modifiers;
    graph_.available = function.body.has_value();
    if (!function.modifiers.empty()) graph_.complete = false;
    if (!graph_.available) {
      graph_.complete = false;
      graph_.unavailable_reason = "Function has no executable body";
      return;
    }
    graph_.entry = add_synthetic(CfgNodeKind::entry);
    graph_.normal_exit = add_synthetic(CfgNodeKind::normal_exit);
    graph_.exceptional_exit = add_synthetic(CfgNodeKind::exceptional_exit);
    const auto body = build_statement(*function.body, graph_.normal_exit);
    add_edge(graph_.entry, body.entry, CfgEdgeKind::normal);
  }

  CfgGraph finish() { return std::move(graph_); }

 private:
  const Function& function_;
  CfgGraph graph_;
  GraphNodeId next_node_{1};
  GraphEdgeId next_edge_{1};

  GraphNodeId add_synthetic(CfgNodeKind kind) {
    CfgNode node;
    node.id = graph_id(); node.kind = kind; node.contract = function_.contract;
    node.function = function_.id; node.synthetic = true;
    graph_.nodes.push_back(std::move(node));
    return graph_.nodes.back().id;
  }

  GraphNodeId add_statement(const Statement& statement) {
    CfgNode node;
    node.id = graph_id(); node.kind = statement.kind == StatementKind::branch ? CfgNodeKind::branch :
      statement.kind == StatementKind::return_statement ? CfgNodeKind::return_statement :
      statement.kind == StatementKind::revert_statement ? CfgNodeKind::revert_statement :
      statement.kind == StatementKind::unsupported ? CfgNodeKind::unsupported : CfgNodeKind::statement;
    node.contract = function_.contract; node.function = function_.id; node.statement = statement.id;
    node.predicate = statement.predicate; node.location = statement.location;
    for (const auto& call : statement.calls) node.calls.push_back(call.id);
    for (const auto& access : statement.state_accesses) node.state_accesses.push_back(access.id);
    node.complete = statement.kind != StatementKind::unsupported;
    if (!statement.evaluation_order_known) {
      node.complete = false;
      node.uncertainty = "Effects belong to one statement; their relative order is unknown";
    }
    if (statement.kind == StatementKind::unsupported) {
      node.uncertainty = "Unsupported statement flow is not connected as known fall-through";
      graph_.complete = false;
    }
    // Unknown subexpression order does not obscure statement-level edges.
    graph_.nodes.push_back(std::move(node));
    const auto id = graph_.nodes.back().id;
    graph_.statement_nodes[statement.id].push_back(id);
    for (const auto& call : statement.calls) graph_.call_nodes[call.id].push_back(id);
    for (const auto& access : statement.state_accesses) graph_.state_access_nodes[access.id].push_back(id);
    return id;
  }

  GraphNodeId graph_id() { return (function_.id << 32) | next_node_++; }

  bool literal(const Statement& statement, bool& value) const {
    const auto find = [&](const auto& self, const Expression& expression) -> const Expression* {
      if (expression.id == statement.predicate) return &expression;
      for (const auto& child : expression.children) if (const auto* found = self(self, child)) return found;
      return nullptr;
    };
    for (const auto& expression : statement.expressions) {
      if (const auto* predicate = find(find, expression); predicate && predicate->kind == ExpressionKind::literal &&
          (predicate->name == "true" || predicate->name == "false")) {
        value = predicate->name == "true"; return true;
      }
    }
    return false;
  }

  void add_edge(GraphNodeId from, GraphNodeId to, CfgEdgeKind kind, bool known = true,
                std::string uncertainty = {}) {
    if (!from || !to) return;
    graph_.edges.push_back({next_edge_++, from, to, kind, known, std::move(uncertainty)});
  }

  Flow build_sequence(const std::vector<Statement>& statements, GraphNodeId continuation) {
    Flow rest{continuation, true};
    for (auto it = statements.rbegin(); it != statements.rend(); ++it)
      rest = build_statement(*it, rest.entry, rest.normal);
    return rest;
  }

  Flow build_statement(const Statement& statement, GraphNodeId continuation, bool continuation_possible = true) {
    const auto id = add_statement(statement);
    if (statement.kind == StatementKind::unsupported) return {id, false};
    if (statement.kind == StatementKind::return_statement) {
      add_edge(id, graph_.normal_exit, CfgEdgeKind::normal_return); return {id, false};
    }
    if (statement.kind == StatementKind::revert_statement) {
      add_edge(id, graph_.exceptional_exit, CfgEdgeKind::exceptional); return {id, false};
    }
    if (statement.kind == StatementKind::block) {
      const auto body = build_sequence(statement.statements, continuation);
      add_edge(id, body.entry, CfgEdgeKind::normal);
      return {id, body.normal && continuation_possible};
    }
    if (statement.kind == StatementKind::branch) {
      const auto then_flow = build_sequence(statement.then_body, continuation);
      const auto else_flow = statement.else_body.empty() ? Flow{continuation, true} :
        build_sequence(statement.else_body, continuation);
      bool value = false;
      const bool known = literal(statement, value);
      if (!known || value) add_edge(id, then_flow.entry, CfgEdgeKind::true_branch);
      if (!known || !value) add_edge(id, else_flow.entry, CfgEdgeKind::false_branch);
      return {id, (then_flow.normal || else_flow.normal) && continuation_possible};
    }
    if (statement.kind == StatementKind::require_guard || statement.kind == StatementKind::assert_guard) {
      bool value = false;
      const bool known = literal(statement, value);
      if (!known || value) add_edge(id, continuation, CfgEdgeKind::true_branch);
      if (!known || !value) add_edge(id, graph_.exceptional_exit, CfgEdgeKind::false_branch);
      return {id, continuation_possible && (!known || value)};
    }
    add_edge(id, continuation, CfgEdgeKind::normal);
    return {id, continuation_possible};
  }
};

QueryResult invalid(const std::string& reason) { return {QueryStatus::invalid, reason}; }
std::unordered_set<GraphNodeId> walk(const CfgGraph& graph, GraphNodeId start,
                                     GraphEdgeId skip = 0, CfgEdgeKind required = CfgEdgeKind::normal,
                                     bool filter = false) {
  std::unordered_set<GraphNodeId> seen{start};
  std::queue<GraphNodeId> pending; pending.push(start);
  while (!pending.empty()) {
    const auto current = pending.front(); pending.pop();
    for (const auto& edge : graph.edges) {
      if (edge.from != current || edge.id == skip || (filter && edge.kind != required)) continue;
      if (edge.known && seen.insert(edge.to).second) pending.push(edge.to);
    }
  }
  return seen;
}

bool valid_pair(const CfgGraph& graph, GraphNodeId first, GraphNodeId second, std::string& reason) {
  const auto* a = graph.node(first); const auto* b = graph.node(second);
  if (!a || !b) { reason = "Unknown graph node ID"; return false; }
  if (a->function != graph.function || b->function != graph.function) { reason = "Nodes belong to another function"; return false; }
  return true;
}
} // namespace

const CfgNode* CfgGraph::node(GraphNodeId id) const {
  const auto found = std::find_if(nodes.begin(), nodes.end(), [id](const auto& item) { return item.id == id; });
  return found == nodes.end() ? nullptr : &*found;
}
const CfgEdge* CfgGraph::edge(GraphEdgeId id) const {
  const auto found = std::find_if(edges.begin(), edges.end(), [id](const auto& item) { return item.id == id; });
  return found == edges.end() ? nullptr : &*found;
}
QueryResult CfgGraph::reachable(GraphNodeId target) const {
  const auto* candidate = node(target); if (!candidate) return invalid("Unknown graph node ID");
  const auto reached = walk(*this, entry);
  if (reached.contains(target)) return {QueryStatus::yes, "A known path reaches the node"};
  return complete ? QueryResult{QueryStatus::no, "No known path reaches the node"} :
    QueryResult{QueryStatus::unknown, "Unsupported or incomplete flow may affect reachability"};
}
QueryResult CfgGraph::ordered(GraphNodeId first, GraphNodeId second) const {
  std::string reason; if (!valid_pair(*this, first, second, reason)) return invalid(reason);
  if (first == second) return {QueryStatus::no, "Strict ordering requires distinct nodes"};
  if (!reachable(first).is_yes()) return reachable(first);
  const auto reached = walk(*this, first);
  if (reached.contains(second)) return {QueryStatus::yes, "A structural path can visit the nodes in order"};
  return complete ? QueryResult{QueryStatus::no, "No known structural path visits the nodes in order"} :
    QueryResult{QueryStatus::unknown, "Unsupported or incomplete flow may hide a path"};
}
QueryResult CfgGraph::ordered(const std::vector<GraphNodeId>& sequence) const {
  if (sequence.empty()) return invalid("Ordered sequence cannot be empty");
  for (const auto id : sequence)
    if (!node(id) || node(id)->function != function) return invalid("Unknown or foreign graph node ID");
  if (!reachable(sequence.front()).is_yes()) return reachable(sequence.front());
  for (std::size_t i = 1; i < sequence.size(); ++i) {
    const auto result = ordered(sequence[i - 1], sequence[i]);
    if (result.status != QueryStatus::yes) return result;
  }
  return {QueryStatus::yes, "A structural path can visit the sequence in order"};
}
QueryResult CfgGraph::ordered_effects(IrId first, IrId second) const {
  const auto locate = [this](IrId id) -> GraphNodeId {
    if (const auto calls = nodes_for_call(id); !calls.empty()) return calls.front();
    if (const auto accesses = nodes_for_state_access(id); !accesses.empty()) return accesses.front();
    return 0;
  };
  const auto first_node = locate(first); const auto second_node = locate(second);
  if (!first_node || !second_node) return invalid("Unknown call or state-access ID");
  if (first_node == second_node) {
    const auto* owner = node(first_node);
    if (owner && !owner->complete) return {QueryStatus::unknown, "Effects in one statement have no known relative order"};
    return {QueryStatus::no, "Strict ordering requires effects in distinct statements"};
  }
  return ordered(first_node, second_node);
}
QueryResult CfgGraph::branch_reachable(GraphNodeId branch, CfgEdgeKind kind, GraphNodeId target) const {
  const auto* source = node(branch); const auto* destination = node(target);
  if (!source || !destination) return invalid("Unknown graph node ID");
  if (source->function != function || destination->function != function) return invalid("Nodes belong to another function");
  if (kind != CfgEdgeKind::true_branch && kind != CfgEdgeKind::false_branch)
    return invalid("Select a true or false branch edge");
  if (source->predicate == no_id) return invalid("Source has no branch predicate");
  const auto source_reachable = reachable(branch);
  if (!source_reachable.is_yes()) return source_reachable;
  std::unordered_set<GraphNodeId> reached;
  for (const auto& edge : edges) {
    if (edge.from == branch && edge.kind == kind && edge.known) {
      const auto downstream = walk(*this, edge.to);
      reached.insert(downstream.begin(), downstream.end());
    }
  }
  if (reached.contains(target)) return {QueryStatus::yes, "A selected branch edge can reach the node"};
  return complete ? QueryResult{QueryStatus::no, "The selected branch cannot reach the node"} :
    QueryResult{QueryStatus::unknown, "Unsupported or incomplete flow may affect branch reachability"};
}
QueryResult CfgGraph::dominates(GraphNodeId dominator, GraphNodeId target) const {
  std::string reason; if (!valid_pair(*this, dominator, target, reason)) return invalid(reason);
  if (!reachable(target).is_yes()) return reachable(target);
  if (dominator == entry || dominator == target) return {QueryStatus::yes, "The node is trivially on every represented path"};
  std::unordered_set<GraphNodeId> seen{entry};
  std::queue<GraphNodeId> pending; pending.push(entry);
  while (!pending.empty()) {
    const auto current = pending.front(); pending.pop();
    for (const auto& edge : edges) if (edge.from == current && edge.to != dominator && edge.known && seen.insert(edge.to).second) pending.push(edge.to);
  }
  if (!seen.contains(target)) return complete ? QueryResult{QueryStatus::yes, "Every represented path to the target passes through the node"} :
    QueryResult{QueryStatus::unknown, "Incomplete flow prevents a dominance proof"};
  return {QueryStatus::no, "A represented path reaches the target without the node"};
}
std::vector<GraphNodeId> CfgGraph::nodes_for_statement(IrId id) const { return statement_nodes.contains(id) ? statement_nodes.at(id) : std::vector<GraphNodeId>{}; }
std::vector<GraphNodeId> CfgGraph::nodes_for_call(IrId id) const { return call_nodes.contains(id) ? call_nodes.at(id) : std::vector<GraphNodeId>{}; }
std::vector<GraphNodeId> CfgGraph::nodes_for_state_access(IrId id) const { return state_access_nodes.contains(id) ? state_access_nodes.at(id) : std::vector<GraphNodeId>{}; }

CfgGraph build_cfg(const Function& function, const std::vector<Limitation>& limitations) { return Builder(function, limitations).finish(); }
CfgProgram build_cfg(const Program& program) {
  CfgProgram result;
  for (const auto& contract : program.contracts)
    for (const auto& function : contract.functions) result.functions.push_back(build_cfg(function, program.limitations));
  return result;
}
} // namespace smartshield