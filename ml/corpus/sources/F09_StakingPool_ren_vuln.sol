// SPDX-License-Identifier: MIT
// Family: F09 — StakingPool
// Pattern: Reentrancy via claimReward - reads reward balance, transfers via call, then updates reward
pragma solidity ^0.8.20;

contract StakingPoolRen {
    address public owner;
    mapping(address => uint256) public rewards;

    constructor() {
        owner = msg.sender;
    }

    function depositReward(address user) external payable {
        rewards[user] += msg.value;
    }

    // REN-001: checks rewards, external call, then zeroes rewards
    // UEC-001: call result not checked
    function claimReward() external {
        uint256 amount = rewards[msg.sender];
        require(amount > 0, "no reward");
        msg.sender.call{value: amount}("");
        rewards[msg.sender] = 0;
    }
}
