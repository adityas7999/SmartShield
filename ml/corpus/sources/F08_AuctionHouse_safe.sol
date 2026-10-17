// SPDX-License-Identifier: MIT
// Family: F08 — AuctionHouse (safe variant)
// Pattern: Pull payment pattern with CEI and msg.sender auth — all rules negative
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract AuctionHouseSafe {
    address public owner;
    address public highestBidder;
    uint256 public highestBid;
    mapping(address => uint256) public pendingReturns;
    bool public ended;

    constructor() {
        owner = msg.sender;
    }

    function bid() external payable {
        require(!ended, "auction ended");
        require(msg.value > highestBid, "bid too low");
        if (highestBidder != address(0)) {
            pendingReturns[highestBidder] += highestBid;
        }
        highestBidder = msg.sender;
        highestBid = msg.value;
    }

    // REN-001 negative: CEI applied — state update before external call
    function withdraw() external {
        uint256 amount = pendingReturns[msg.sender];
        require(amount > 0, "nothing to withdraw");
        pendingReturns[msg.sender] = 0;  // effects first
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }

    // TXO-001 negative: msg.sender used
    function endAuction() external {
        require(msg.sender == owner, "not owner");
        ended = true;
        (bool ok, ) = owner.call{value: highestBid}("");
        require(ok, "payout failed");
    }
}
