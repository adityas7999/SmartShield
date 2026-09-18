// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VulnerableOwnerWallet {
    address public owner;
    mapping(address => uint256) public balances;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(address payable recipient, uint256 amount) external {
        require(tx.origin == owner, "not owner");
        require(address(this).balance >= amount, "insufficient funds");
        recipient.transfer(amount);
    }
}
