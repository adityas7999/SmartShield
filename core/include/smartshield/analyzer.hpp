#pragma once

#include <cstddef>
#include <optional>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

namespace smartshield {

struct SourceLocation {
  std::string file;
  int line{1};
  int column{1};
  std::size_t offset{0};
  std::size_t length{0};
};

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
