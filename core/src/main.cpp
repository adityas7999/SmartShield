#include "smartshield/analyzer.hpp"

#include <exception>
#include <iostream>
#include <string>

#include <nlohmann/json.hpp>

int main() {
  try {
    const auto request = nlohmann::json::parse(std::cin);
    if (!request.contains("compilerOutput") || !request.contains("source") ||
        !request.contains("fileName")) {
      throw std::runtime_error(
          "Analyzer input requires compilerOutput, source, and fileName");
    }

    smartshield::Analyzer analyzer;
    const auto result = analyzer.analyze(request.at("compilerOutput"),
                                         request.at("source").get<std::string>(),
                                         request.at("fileName").get<std::string>());
    std::cout << result.dump() << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "SmartShield analyzer error: " << error.what() << '\n';
    return 2;
  }
}
