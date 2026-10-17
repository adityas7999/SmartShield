// SPDX-License-Identifier: MIT
// Family: F11 — FlashLoanReceiver
// Pattern: Flash loan receiver performing low-level call without checking return value
pragma solidity ^0.8.20;

contract FlashLoanReceiverVuln {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    // UEC-001: low-level call return result discarded
    function executeOperation(address token, uint256 amount, bytes calldata params) external {
        require(msg.sender == owner, "not owner");
        token.call(params);
    }
}
