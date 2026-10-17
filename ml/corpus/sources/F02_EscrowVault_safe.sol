// SPDX-License-Identifier: MIT
// Family: F02 — EscrowVault (safe CEI variant)
// Pattern: Checks-effects-interactions correctly applied
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract EscrowVaultSafe {
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
        // CEI: update state BEFORE external call
        deposits[beneficiary] = 0;
        (bool ok, ) = beneficiary.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
