cmake_minimum_required(VERSION 3.20)

project(smartshield_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)
find_package(nlohmann_json 3.11.3 QUIET)

if(NOT nlohmann_json_FOUND)
  FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
  )
  FetchContent_MakeAvailable(nlohmann_json)
endif()

add_library(smartshield_analysis src/analyzer.cpp src/ir.cpp)
target_include_directories(smartshield_analysis PUBLIC include)
target_link_libraries(smartshield_analysis PUBLIC nlohmann_json::nlohmann_json)
target_compile_options(smartshield_analysis PRIVATE -Wall -Wextra -Wpedantic)

add_executable(smartshield-analyzer src/main.cpp)
target_link_libraries(smartshield-analyzer PRIVATE smartshield_analysis)

include(CTest)
if(BUILD_TESTING)
  add_executable(smartshield-core-tests tests/analyzer_test.cpp)
  target_link_libraries(smartshield-core-tests PRIVATE smartshield_analysis)
  add_test(NAME smartshield-core-tests COMMAND smartshield-core-tests)
  add_executable(smartshield-ir-tests tests/ir_test.cpp)
  target_link_libraries(smartshield-ir-tests PRIVATE smartshield_analysis)
  find_program(NODE_EXECUTABLE node)
  if(NODE_EXECUTABLE AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../backend/solc/node_modules/solc/index.js")
    add_test(NAME smartshield-ir-fixtures
      COMMAND "${NODE_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/ir_fixtures.mjs" $<TARGET_FILE:smartshield-ir-tests>)
  else()
    message(WARNING "IR fixture tests require Node and: npm ci --prefix ../backend/solc. Reconfigure after installing.")
  endif()
endif()
