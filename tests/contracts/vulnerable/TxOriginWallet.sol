// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// @custom-id TXO-DIR-01
// @custom-vulnerability tx-origin-authorization
// @custom-expected vulnerable
// @custom-location line 17
// @custom-reasoning Direct require(tx.origin == owner) authorization guard controlling ether transfer. Attacker contracts can trick owner into calling them to drain wallet.
// @custom-reference SWC-115 / Solidity Documentation
// @custom-reviewer Aditya
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
