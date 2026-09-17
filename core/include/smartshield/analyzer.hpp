#pragma once

#include <cstddef>
#include <nlohmann/json.hpp>
#include <optional>
#include <string>
#include <vector>

#include "smartshield/ir.hpp"

namespace smartshield {

class Analyzer {
 public:
  nlohmann::json analyze(const nlohmann::json& compiler_output,
                         const std::string& source,
                         const std::string& file_name) const;
};

}  // namespace smartshield
