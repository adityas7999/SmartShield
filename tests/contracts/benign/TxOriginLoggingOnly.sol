// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// @custom-id TXO-NEG-01
// @custom-vulnerability tx-origin-authorization
// @custom-expected benign
// @custom-location line 26
// @custom-reasoning tx.origin is utilized for audit logging and anti-bot verification (tx.origin == msg.sender), but actual privilege authorization is strictly gated by msg.sender == owner.
// @custom-reference ConsenSys Best Practices
// @custom-reviewer Aditya
contract TxOriginLoggingOnly {
    address public owner;

    event ActionLogged(address indexed origin, address indexed caller, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    function safeWithdraw(address payable recipient, uint256 amount) external {
        require(msg.sender == owner, "Unauthorized: msg.sender is not owner");
        require(tx.origin == msg.sender, "Intermediary contracts disallowed");

        emit ActionLogged(tx.origin, msg.sender, amount);
        recipient.transfer(amount);
    }

    receive() external payable {}
}
