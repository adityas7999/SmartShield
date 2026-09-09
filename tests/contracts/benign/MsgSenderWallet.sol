// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// @custom-id TXO-SAF-01
// @custom-vulnerability tx-origin-authorization
// @custom-expected benign
// @custom-location line 16
// @custom-reasoning Authorization is enforced using msg.sender == owner instead of tx.origin, ensuring intermediary contracts cannot bypass authorization.
// @custom-reference SWC-115 Remediation Guide
// @custom-reviewer Aditya
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
