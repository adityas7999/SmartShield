#include "smartshield/reentrancy_detector.hpp"

#include <iostream>
#include <stdexcept>
#include <string>

namespace {

using smartshield::AccessKind;
using smartshield::Call;
using smartshield::CallKind;
using smartshield::Contract;
using smartshield::Expression;
using smartshield::ExpressionKind;
using smartshield::Function;
using smartshield::Program;
using smartshield::Resolution;
using smartshield::SourceLocation;
using smartshield::StateAccess;
using smartshield::Statement;
using smartshield::StatementKind;
using smartshield::Variable;
using smartshield::VariableKind;

void expect(bool condition, const std::string& message) {
  if (!condition) throw std::runtime_error(message);
}

SourceLocation location(int line) {
  return {"Fixture.sol", line, 1, 0, 1, true};
}

Expression key(smartshield::IrId id, const std::string& text) {
  Expression expression;
  expression.id = id;
  expression.kind = text == "dynamicKey" ? ExpressionKind::call : ExpressionKind::identifier;
  expression.name = text;
  expression.text = text;
  expression.location = location(1);
  expression.resolution = expression.kind == ExpressionKind::call
                              ? Resolution::unresolved : Resolution::resolved;
  expression.variable = text == "msg.sender" ? 42 : text == "recipient" ? 43 : 0;
  return expression;
}

Statement state_statement(smartshield::IrId statement_id, smartshield::IrId expression_id,
                          smartshield::IrId key_id, AccessKind action,
                          const std::string& key_text, int line) {
  Statement statement;
  statement.id = statement_id;
  statement.kind = StatementKind::expression;
  statement.location = location(line);
  Expression path;
  path.id = expression_id;
  path.kind = ExpressionKind::index;
  path.text = "balances[" + key_text + "]";
  path.location = location(line);
  path.children.push_back(key(key_id, key_text));
  statement.expressions.push_back(path);
  statement.state_accesses.push_back({statement_id + 100, 1, expression_id, statement_id,
                                      1, action, {key_id}, location(line)});
  return statement;
}

Statement call_statement(smartshield::IrId statement_id, int line,
                         CallKind kind = CallKind::low_level) {
  Statement statement;
  statement.id = statement_id;
  statement.kind = StatementKind::expression;
  statement.location = location(line);
  Call call;
  call.id = statement_id + 100;
  call.statement = statement_id;
  call.function = 1;
  call.kind = kind;
  call.resolution = Resolution::syntax_only;
  call.location = location(line);
  call.name = "call";
  statement.calls.push_back(call);
  return statement;
}

Program program_with_statements(const std::vector<Statement>& statements) {
  Statement body;
  body.id = 10;
  body.kind = StatementKind::block;
  body.statements = statements;

  Function function;
  function.id = 1;
  function.name = "withdraw";
  function.body = body;

  Contract contract;
  contract.id = 2;
  contract.name = "Vault";
  contract.functions.push_back(function);

  Program program;
  program.contracts.push_back(contract);
  return program;
}

Program program_with(const Statement& first, const Statement& call, const Statement& last) {
  return program_with_statements({first, call, last});
}

}  // namespace

int main() {
  try {
    const auto read = state_statement(11, 111, 112, AccessKind::read, "msg.sender", 10);
    const auto call = call_statement(12, 11);
    const auto write = state_statement(13, 113, 114, AccessKind::write, "msg.sender", 12);
    const auto finding = smartshield::ReentrancyDetector().detect(program_with(read, call, write));
    expect(finding.size() == 1, "matching post-call state write should produce REN-001");
    expect(finding[0]["detectorId"] == "REN-001", "detector ID should be REN-001");
    expect(finding[0]["confidence"] == "high", "resolved direct storage should be high confidence");

    const auto safe = smartshield::ReentrancyDetector().detect(program_with(
        read, write, call));
    expect(safe.empty(), "state written before the call must not produce REN-001");

    const auto unrelated = state_statement(13, 113, 114, AccessKind::write, "msg.sender", 12);
    auto unrelated_program = program_with(read, call, unrelated);
    auto unrelated_contract = unrelated_program.contracts.front();
    unrelated_contract.functions.front().body->statements[2].state_accesses.front().variable = 2;
    unrelated_program.contracts.front() = unrelated_contract;
    expect(smartshield::ReentrancyDetector().detect(unrelated_program).empty(),
           "a different state variable must not produce REN-001");

    const auto unresolved = state_statement(13, 113, 114, AccessKind::write, "dynamicKey", 12);
    const auto unresolved_findings = smartshield::ReentrancyDetector().detect(
        program_with(read, call, unresolved));
    expect(unresolved_findings.size() == 1, "unresolved key relation should remain a potential finding");
    expect(unresolved_findings[0]["confidence"] == "medium",
           "unresolved key relation must lower confidence");

    auto unknown_findings = smartshield::ReentrancyDetector().detect(
      program_with(read, call_statement(12, 11, CallKind::unknown), write));
    expect(unknown_findings.size() == 1 && unknown_findings[0]["confidence"] == "medium",
         "unknown calls must not produce high-confidence findings");
    expect(!unknown_findings[0]["limitations"].empty(),
         "unknown calls must retain a limitation");

    auto modified_program = program_with(read, call, write);
    modified_program.contracts.front().functions.front().modifiers.push_back({
      99, "guard", {}, location(2), Resolution::unresolved});
    const auto modified_findings = smartshield::ReentrancyDetector().detect(modified_program);
    expect(modified_findings[0]["confidence"] == "medium",
         "modifiers must prevent a high-confidence guard claim");

    Statement branch;
    branch.id = 20;
    branch.kind = StatementKind::branch;
    const auto branch_analysis = smartshield::ReentrancyDetector().analyze(
      program_with_statements({read, branch, call, write}));
    expect(branch_analysis.findings.empty(), "control-flow boundaries must not create a path finding");
    expect(!branch_analysis.limitations.empty(),
         "control-flow boundaries must retain a pre-CFG limitation");

    const auto two_findings = smartshield::ReentrancyDetector().detect(
      program_with_statements({read, call, write,
                   state_statement(14, 115, 116, AccessKind::read, "msg.sender", 14),
                   call_statement(15, 15),
                   state_statement(16, 117, 118, AccessKind::write, "msg.sender", 16)}));
    expect(two_findings.size() == 2, "independent direct candidates must both be retained");

    std::cout << "SmartShield REN-001 tests passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Test failure: " << error.what() << '\n';
    return 1;
  }
}
