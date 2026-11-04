// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TMP-DIR-01
// Purpose: Timestamp-dependent game logic and payout.

contract TimestampLottery {
    address public owner;
    uint256 public deadline;

    constructor(uint256 _deadline) {
        owner = msg.sender;
        deadline = _deadline;
    }

    function claimPrize(address payable winner) external {
        require(block.timestamp == deadline, "not deadline");
        winner.transfer(1 ether);
    }
}
