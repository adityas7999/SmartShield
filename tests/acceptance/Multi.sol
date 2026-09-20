// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TreasuryMultiIssue {
    address public owner;
    mapping(address => uint256) public balances;
    bool private entered;

    constructor() {
        owner = msg.sender;
    }

    function replaceOwner(address newOwner) external {
        owner = newOwner;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        require(tx.origin == owner, "not owner");
        require(balances[msg.sender] > 0, "empty balance");

        msg.sender.call("");
        balances[msg.sender] = 0;
    }
}
