#pragma once

#include "smartshield/ir.hpp"
#include <nlohmann/json_fwd.hpp>

namespace smartshield {

// Only this adapter knows Solidity AST field names. IR consumers do not need JSON.
Program build_ir(const nlohmann::json& compiler_output,
                 const std::string& source, const std::string& file_name);

} // namespace smartshield
