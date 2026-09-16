#pragma once

#include "smartshield/ir.hpp"

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace smartshield {

using GraphNodeId = std::uint64_t;
using GraphEdgeId = std::uint64_t;

enum class CfgNodeKind { entry, normal_exit, exceptional_exit, statement, branch,
                         return_statement, revert_statement, unsupported };
enum class CfgEdgeKind { normal, true_branch, false_branch, normal_return,
                         exceptional };
enum class QueryStatus { yes, no, unknown, invalid };

struct QueryResult {
  QueryStatus status{QueryStatus::invalid};
  std::string reason;
  bool is_yes() const { return status == QueryStatus::yes; }
};

struct CfgNode {
  GraphNodeId id{0};
  CfgNodeKind kind{CfgNodeKind::statement};
  IrId contract{no_id};
  IrId function{no_id};
  IrId statement{no_id};
  IrId predicate{no_id};
  SourceLocation location;
  std::vector<IrId> calls;
  std::vector<IrId> state_accesses;
  bool synthetic{false};
  bool complete{true};
  std::string uncertainty;
};

struct CfgEdge {
  GraphEdgeId id{0};
  GraphNodeId from{0};
  GraphNodeId to{0};
  CfgEdgeKind kind{CfgEdgeKind::normal};
  bool known{true};
  std::string uncertainty;
};

struct CfgGraph {
  IrId contract{no_id};
  IrId function{no_id};
  bool available{false};
  bool complete{true};
  std::string unavailable_reason;
  GraphNodeId entry{0};
  GraphNodeId normal_exit{0};
  GraphNodeId exceptional_exit{0};
  std::vector<CfgNode> nodes;
  std::vector<CfgEdge> edges;
  std::vector<Limitation> limitations;
  std::vector<ModifierApplication> modifiers;
  std::unordered_map<IrId, std::vector<GraphNodeId>> statement_nodes;
  std::unordered_map<IrId, std::vector<GraphNodeId>> call_nodes;
  std::unordered_map<IrId, std::vector<GraphNodeId>> state_access_nodes;

  const CfgNode* node(GraphNodeId id) const;
  const CfgEdge* edge(GraphEdgeId id) const;
  QueryResult reachable(GraphNodeId target) const;
  QueryResult ordered(GraphNodeId first, GraphNodeId second) const;
  QueryResult ordered(const std::vector<GraphNodeId>& sequence) const;
  QueryResult ordered_effects(IrId first, IrId second) const;
  QueryResult branch_reachable(GraphNodeId branch, CfgEdgeKind branch_kind,
                               GraphNodeId target) const;
  QueryResult dominates(GraphNodeId dominator, GraphNodeId target) const;
  std::vector<GraphNodeId> nodes_for_statement(IrId statement_id) const;
  std::vector<GraphNodeId> nodes_for_call(IrId call_id) const;
  std::vector<GraphNodeId> nodes_for_state_access(IrId access_id) const;
};

struct CfgProgram {
  std::vector<CfgGraph> functions;
};

CfgGraph build_cfg(const Function& function, const std::vector<Limitation>& limitations = {});
CfgProgram build_cfg(const Program& program);

} // namespace smartshield