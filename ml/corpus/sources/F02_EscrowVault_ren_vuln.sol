// SPDX-License-Identifier: MIT
// Family: F02 — EscrowVault
// Pattern: Reentrancy — checks storage, calls external, updates storage after
// Expected: TXO-001 negative, REN-001 positive, ACC-001 negative, UEC-001 positive
pragma solidity ^0.8.20;

contract EscrowVault {
    address public owner;
    mapping(address => uint256) public deposits;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {
        deposits[msg.sender] += msg.value;
    }

    function release(address beneficiary) external {
        require(msg.sender == owner, "not owner");
        uint256 amount = deposits[beneficiary];
        require(amount > 0, "nothing to release");
        // REN-001: checks deposits[beneficiary], calls external, THEN updates deposits[beneficiary]
        beneficiary.call{value: amount}("");
        deposits[beneficiary] = 0;
    }
}
