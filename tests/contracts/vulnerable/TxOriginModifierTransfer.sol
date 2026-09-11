// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-id TXO-VAR-01
/// @custom-vulnerability tx-origin-authorization
/// @custom-expected vulnerable
/// @custom-location line 23
/// @custom-reasoning Authorization logic is encapsulated in onlyOriginOwner modifier comparing tx.origin to owner. Guard controls sensitive state mutations (transferOwnership) and balance drainage.
/// @custom-reference SWC-115 / ConsenSys Best Practices
/// @custom-reviewer Aditya
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

