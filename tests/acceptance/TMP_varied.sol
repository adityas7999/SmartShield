// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract T {
    uint256 public deadline;
    uint256 public executed;

    function checkAndRun() external {
        if (block.timestamp == deadline) {
            executed += 1;
        }
    }
}
