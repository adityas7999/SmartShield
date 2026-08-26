// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-vulnerability tx-origin-authorization
/// @custom-expected vulnerable
/// @custom-location require(tx.origin == owner)
/// @custom-reference Solidity security considerations: tx.origin should not be used for authorization
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
