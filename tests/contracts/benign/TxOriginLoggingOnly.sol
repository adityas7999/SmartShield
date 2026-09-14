// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TXO-NEG-01
// Purpose: See expected-results.json for scope and reasoning.
contract TxOriginLoggingOnly {
    address public owner;

    event ActionLogged(address indexed origin, address indexed caller, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    function safeWithdraw(address payable recipient, uint256 amount) external {
        require(msg.sender == owner, "Unauthorized: msg.sender is not owner");

        emit ActionLogged(tx.origin, msg.sender, amount);
        recipient.transfer(amount);
    }

    receive() external payable {}
}
