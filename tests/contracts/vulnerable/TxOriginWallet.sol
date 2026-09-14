// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TXO-DIR-01
// Purpose: Direct origin-based authorization.


contract TxOriginWallet {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdraw(address payable recipient, uint256 amount) external {
        require(tx.origin == owner, "not owner");
        recipient.transfer(amount);
    }
}
