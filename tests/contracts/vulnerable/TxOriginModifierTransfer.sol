// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TXO-VAR-01
// Purpose: See expected-results.json for scope and reasoning.
contract TxOriginModifierTransfer {
    address public owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOriginOwner() {
        require(tx.origin == owner, "Caller not tx.origin owner");
        _;
    }

    function transferOwnership(address newOwner) external onlyOriginOwner {
        require(newOwner != address(0), "Zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function emergencyWithdraw(address payable recipient) external onlyOriginOwner {
        recipient.transfer(address(this).balance);
    }

    receive() external payable {}
}
