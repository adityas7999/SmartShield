#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace smartshield {

using IrId = std::uint64_t;
constexpr IrId no_id = 0;

struct SourceLocation {
  std::string file;
  int line{1};
  int column{1}; // One-based UTF-8 byte column, matching solc byte offsets.
  std::size_t offset{0};
  std::size_t length{0};
  bool available{false};
};

enum class Resolution { resolved, syntax_only, unresolved, unsupported };
struct Limitation {
  IrId entity{no_id};
  SourceLocation location;
  std::string message;
};

enum class ExpressionKind { unknown, literal, identifier, builtin, member, index,
                            binary, unary, assignment, call, call_options, tuple, type };
struct Expression {
  IrId id{no_id};
  ExpressionKind kind{ExpressionKind::unknown};
  std::string name; // Identifier, member, builtin, or literal value.
  std::string op;
  bool prefix{true}; // Unary ++/--: retain prefix versus postfix syntax.
  std::string text; // Display only; never used to classify code.
  SourceLocation location;
  Resolution resolution{Resolution::unresolved};
  IrId variable{no_id};
  std::vector<Expression> children; // Operand order, not execution order.
  std::vector<std::string> names; // Named call arguments/options; tuple holes are unknown children.
};

enum class VariableKind { state, parameter, local, return_value };
struct Variable {
  IrId id{no_id};
  std::string name;
  std::string type;
  VariableKind kind{VariableKind::local};
  std::string storage;
  SourceLocation location;
};

enum class CallKind { builtin, conversion, internal, external_member, low_level,
                      transfer, send, delegatecall, staticcall, unknown };
struct Call {
  IrId id{no_id};
  IrId expression{no_id};
  IrId statement{no_id};
  IrId function{no_id};
  CallKind kind{CallKind::unknown};
  Resolution resolution{Resolution::unresolved};
  std::string name;
  IrId target{no_id};
  std::vector<IrId> arguments;
  std::optional<IrId> value;
  SourceLocation location;
};

enum class AccessKind { read, write };
struct StateAccess {
  IrId id{no_id};
  IrId variable{no_id};
  IrId expression{no_id}; // Full storage path expression, not just its base.
  IrId statement{no_id};
  IrId function{no_id};
  AccessKind action{AccessKind::read};
  std::vector<IrId> keys; // Base to leaf: a[i][j] keeps i, then j.
  SourceLocation location;
};

enum class StatementKind { block, expression, declaration, require_guard, assert_guard,
                           branch, return_statement, revert_statement, emit, unsupported };
struct Statement {
  IrId id{no_id};
  IrId parent{no_id};
  IrId function{no_id};
  StatementKind kind{StatementKind::unsupported};
  SourceLocation location;
  std::vector<Expression> expressions;
  IrId predicate{no_id};
  std::vector<Statement> statements; // Ordered block children.
  std::vector<Statement> then_body; // Zero or one statement (usually a block).
  std::vector<Statement> else_body;
  std::vector<Variable> declarations;
  std::vector<Call> calls; // Directly owned; excludes child statements.
  std::vector<StateAccess> state_accesses;
  bool evaluation_order_known{true};
  bool unchecked{false};
};

struct ModifierApplication {
  IrId id{no_id};
  std::string name;
  std::vector<Expression> arguments;
  SourceLocation location;
  Resolution resolution{Resolution::unresolved};
};

struct Function {
  IrId id{no_id};
  IrId contract{no_id};
  std::string name;
  std::string visibility;
  std::string mutability;
  SourceLocation location;
  std::vector<Variable> parameters;
  std::vector<Variable> returns;
  std::vector<ModifierApplication> modifiers; // Preserved, never expanded into the body.
  std::optional<Statement> body;
};

struct Contract {
  IrId id{no_id};
  std::string name;
  std::string kind;
  SourceLocation location;
  std::vector<Variable> variables;
  std::vector<Function> functions;
};

struct Program {
  std::vector<Contract> contracts;
  std::vector<Limitation> limitations;
};

} // namespace smartshield
