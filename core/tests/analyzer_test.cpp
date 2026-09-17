#include "smartshield/analyzer.hpp"

#include <iostream>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

namespace {

using json = nlohmann::json;

void expect(bool condition, const std::string& message) {
  if (!condition) {
    throw std::runtime_error(message);
  }
}

json identifier(const std::string& name, const std::string& src) {
  return {{"nodeType", "Identifier"}, {"name", name}, {"src", src}};
}

json member(const std::string& base, const std::string& name,
            const std::string& src) {
  return {
      {"nodeType", "MemberAccess"},
      {"memberName", name},
      {"expression", identifier(base, src)},
      {"src", src},
  };
}

json compiler_output_for(const std::string& built_in) {
  const std::string source_name = "Wallet.sol";
  json condition = {
      {"nodeType", "BinaryOperation"},
      {"operator", "=="},
      {"leftExpression",
       member(built_in, built_in == "tx" ? "origin" : "sender", "42:9:0")},
      {"rightExpression", identifier("owner", "55:5:0")},
      {"src", "42:18:0"},
  };
  json guard = {
      {"nodeType", "FunctionCall"},
      {"expression", identifier("require", "34:7:0")},
      {"arguments", json::array({condition})},
      {"src", "34:28:0"},
  };
  json transfer = {
      {"nodeType", "FunctionCall"},
      {"expression",
       {{"nodeType", "MemberAccess"},
        {"memberName", "transfer"},
        {"expression", identifier("recipient", "66:9:0")},
        {"src", "66:18:0"}}},
      {"arguments", json::array()},
      {"src", "66:20:0"},
  };
  json function = {
      {"nodeType", "FunctionDefinition"},
      {"name", "withdraw"},
      {"src", "20:70:0"},
      {"body",
       {{"nodeType", "Block"},
        {"src", "30:60:0"},
        {"statements", json::array({{{"nodeType", "ExpressionStatement"},
                                     {"expression", guard},
                                     {"src", "34:29:0"}},
                                    {{"nodeType", "ExpressionStatement"},
                                     {"expression", transfer},
                                     {"src", "66:21:0"}}})}}},
  };
  json contract = {
      {"nodeType", "ContractDefinition"},
      {"name", "Wallet"},
      {"src", "0:100:0"},
      {"nodes", json::array({function})},
  };
  return {{"sources",
           {{source_name,
             {{"ast",
               {{"nodeType", "SourceUnit"},
                {"src", "0:100:0"},
                {"nodes", json::array({contract})}}}}}}}};
}

}  // namespace

int main() {
  try {
    const std::string source(120, 'x');
    smartshield::Analyzer analyzer;

    const auto parsed =
        analyzer.analyze(compiler_output_for("tx"), source, "Wallet.sol");
    expect(parsed["status"] == "partial", "untyped input must be partial");
    expect(parsed["findings"].empty(),
           "untyped input must not establish findings");
    expect(parsed["ruleResults"].size() == 4, "all four rules need coverage");
    for (const auto& rule : parsed["ruleResults"]) {
      expect(rule["status"] == "unsupported",
             "untyped input must be unsupported");
      expect(!rule["reasons"].empty(), "unsupported requires a reason");
    }
    bool rejected = false;
    try {
      analyzer.analyze(json::object(), source, "Wallet.sol");
    } catch (const std::exception&) {
      rejected = true;
    }
    expect(rejected, "missing AST must be rejected");

    std::cout << "SmartShield core tests passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Test failure: " << error.what() << '\n';
    return 1;
  }
}
