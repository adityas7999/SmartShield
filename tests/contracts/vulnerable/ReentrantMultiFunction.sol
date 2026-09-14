// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: REN-VAR-01
// Purpose: See expected-results.json for scope and reasoning.
contract ReentrantMultiFunction {
    mapping(address => uint256) public userBalances;

    function deposit() external payable {
        userBalances[msg.sender] += msg.value;
    }

    function withdrawAll() external {
        uint256 balance = userBalances[msg.sender];
        require(balance > 0, "No balance");

        (bool success, ) = payable(msg.sender).call{value: balance}("");
        require(success, "Transfer failed");

        userBalances[msg.sender] = 0;
    }

    function transferTo(address recipient, uint256 amount) external {
        require(userBalances[msg.sender] >= amount, "Insufficient balance");
        userBalances[msg.sender] -= amount;
        userBalances[recipient] += amount;
    }
}
