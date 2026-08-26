// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-vulnerability tx-origin-authorization
/// @custom-expected benign
/// @custom-location require(msg.sender == owner)
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
