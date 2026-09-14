// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: REN-DIR-01
// Purpose: Call before balance update; a potential ordering finding.

contract ReentrantVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
        balances[msg.sender] -= amount;
    }
}
