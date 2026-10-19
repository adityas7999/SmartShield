// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Family: F13-TimeLockLottery
// Variant: Safe against TMP-001 (Uses interval comparison >= instead of strict equality)
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative, TMP-001 negative

contract TimeLockLotterySafe {
    address public owner;
    uint256 public claimDeadline;
    mapping(address => uint256) public deposits;

    event PrizeClaimed(address indexed winner, uint256 amount);

    constructor(uint256 _deadline) {
        owner = msg.sender;
        claimDeadline = _deadline;
    }

    function deposit() external payable {
        deposits[msg.sender] += msg.value;
    }

    function claimJackpot(address payable winner) external {
        require(msg.sender == owner, "caller not owner");
        // Safe: Interval inequality comparison (>=) cannot be gamed by 15s timestamp drift
        require(block.timestamp >= claimDeadline, "deadline not reached");

        uint256 payout = address(this).balance;
        winner.transfer(payout);
        emit PrizeClaimed(winner, payout);
    }
}
