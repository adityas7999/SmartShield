// SPDX-License-Identifier: MIT
// Family: F12 — PaymentSplitter
// Pattern: tx.origin used to authorize release of payment
pragma solidity ^0.8.20;

contract PaymentSplitterTxo {
    address public owner;
    address payable public payee;

    constructor(address payable _payee) payable {
        owner = msg.sender;
        payee = _payee;
    }

    // TXO-001: tx.origin used for authorizing payout
    function release() external {
        require(tx.origin == owner, "not authorized");
        (bool ok, ) = payee.call{value: address(this).balance}("");
        require(ok, "payout failed");
    }
}
