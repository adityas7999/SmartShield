// SPDX-License-Identifier: MIT
// Family: F08 — AuctionHouse
// Pattern: tx.origin guard + reentrancy + unchecked refund — multi-rule positive
// Expected: TXO-001 positive, REN-001 positive, ACC-001 negative, UEC-001 positive
pragma solidity ^0.8.20;

contract AuctionHouse {
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

    // REN-001: checks pendingReturns[msg.sender], calls external, THEN updates pendingReturns
    // UEC-001: call result not checked
    function withdraw() external {
        uint256 amount = pendingReturns[msg.sender];
        require(amount > 0, "nothing to withdraw");
        msg.sender.call{value: amount}("");
        pendingReturns[msg.sender] = 0;
    }

    // TXO-001: tx.origin used to restrict endAuction (a state-changing operation)
    function endAuction() external {
        require(tx.origin == owner, "not owner");
        ended = true;
        owner.call{value: highestBid}("");
    }
}
