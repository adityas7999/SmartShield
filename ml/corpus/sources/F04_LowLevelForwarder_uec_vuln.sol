// SPDX-License-Identifier: MIT
// Family: F04 — LowLevelForwarder
// Pattern: Low-level calls with discarded or unchecked return values
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 positive (multiple)
pragma solidity ^0.8.20;

contract LowLevelForwarder {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // UEC-001: call result discarded entirely
    function forwardCallDiscarded(address target, bytes calldata data) external {
        require(msg.sender == owner, "not owner");
        target.call(data);
    }

    // UEC-001: result assigned but never checked or used
    function forwardCallUnused(address target, bytes calldata data) external returns (bool) {
        require(msg.sender == owner, "not owner");
        (bool ok, ) = target.call(data);
        return true; // ok never used
    }

    // UEC-001 negative (safe) — result is required
    function forwardCallSafe(address target, bytes calldata data) external {
        require(msg.sender == owner, "not owner");
        (bool ok, ) = target.call(data);
        require(ok, "call failed");
    }
}
