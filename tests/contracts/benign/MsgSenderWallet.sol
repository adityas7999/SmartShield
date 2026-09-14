// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TXO-SAF-01
// Purpose: Immediate-caller authorization.

contract MsgSenderWallet {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function withdraw(address payable recipient, uint256 amount) external {
        require(msg.sender == owner, "not owner");
        recipient.transfer(amount);
    }
}
