// SPDX-License-Identifier: MIT
// Family: F09 — StakingPool (safe variant)
// Pattern: CEI applied - zeroes reward before transferring
pragma solidity ^0.8.20;

contract StakingPoolSafe {
    address public owner;
    mapping(address => uint256) public rewards;

    constructor() {
        owner = msg.sender;
    }

    function depositReward(address user) external payable {
        rewards[user] += msg.value;
    }

    function claimReward() external {
        uint256 amount = rewards[msg.sender];
        require(amount > 0, "no reward");
        rewards[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
