// SPDX-License-Identifier: MIT
// Family: F11 — FlashLoanReceiver (safe variant)
// Pattern: Low-level call return value strictly checked with require
pragma solidity ^0.8.20;

contract FlashLoanReceiverSafe {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function executeOperation(address token, uint256 amount, bytes calldata params) external {
        require(msg.sender == owner, "not owner");
        (bool success, ) = token.call(params);
        require(success, "call failed");
    }
}
