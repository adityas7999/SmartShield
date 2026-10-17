// SPDX-License-Identifier: MIT
// Family: F04 — LowLevelForwarder (delegatecall variant)
// Pattern: delegatecall result discarded — higher severity UEC-001
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 positive (high)
pragma solidity ^0.8.20;

contract LowLevelDelegateForwarder {
    address public owner;
    address public implementation;

    constructor(address impl) {
        owner = msg.sender;
        implementation = impl;
    }

    // UEC-001 (high severity): delegatecall result discarded
    function upgrade(address newImpl, bytes calldata initData) external {
        require(msg.sender == owner, "not owner");
        implementation = newImpl;
        implementation.delegatecall(initData);
    }
}
