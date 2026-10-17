// SPDX-License-Identifier: MIT
// Family: F12 — PaymentSplitter (safe variant)
// Pattern: msg.sender used to authorize release of payment
pragma solidity ^0.8.20;

contract PaymentSplitterSafe {
    address public owner;
    address payable public payee;

    constructor(address payable _payee) payable {
        owner = msg.sender;
        payee = _payee;
    }

    function release() external {
        require(msg.sender == owner, "not authorized");
        (bool ok, ) = payee.call{value: address(this).balance}("");
        require(ok, "payout failed");
    }
}
