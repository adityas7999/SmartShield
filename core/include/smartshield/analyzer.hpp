#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>
#include "smartshield/ir.hpp"

namespace smartshield {

struct GuardFact {
  std::string statement_type;
  std::string condition;
  std::string contract_name;
  std::string function_name;
  SourceLocation location;
  std::optional<std::string> sensitive_effect;
};

class Analyzer {
 public:
  nlohmann::json analyze(const nlohmann::json& compiler_output,
                         const std::string& source,
                         const std::string& file_name) const;
};

}  // namespace smartshield
