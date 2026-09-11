#pragma once

#include <nlohmann/json.hpp>

#include "smartshield/ir.hpp"

namespace smartshield {

class ReentrancyDetector {
 public:
  nlohmann::json detect(const Program& program) const;
};

}  // namespace smartshield