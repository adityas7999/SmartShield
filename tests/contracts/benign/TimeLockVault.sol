// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TMP-SAFE-01
// Purpose: Safe interval timestamp inequality lock.

contract TimeLockVault {
    address public owner;
    uint256 public unlockTime;

    constructor(uint256 _unlockTime) {
        owner = msg.sender;
        unlockTime = _unlockTime;
    }

    function withdraw(address payable recipient) external {
        require(msg.sender == owner, "not owner");
        require(block.timestamp >= unlockTime, "still locked");
        recipient.transfer(address(this).balance);
    }
}
