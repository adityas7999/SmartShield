#pragma once

#include <string>
#include <vector>
#include <nlohmann/json.hpp>

#include "smartshield/ir.hpp"

namespace smartshield {

struct ReentrancyAnalysis {
  nlohmann::json findings;
  std::vector<std::string> limitations;
};

class ReentrancyDetector {
 public:
  ReentrancyAnalysis analyze(const Program& program) const;
  nlohmann::json detect(const Program& program) const;
};

}  // namespace smartshield