// SPDX-License-Identifier: MIT
// Family: F03 — OwnerRegistry (safe variant)
// Pattern: Two-step ownership transfer with proper authorization
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract OwnerRegistrySafe {
    address public owner;
    address public pendingOwner;
    string public name;

    constructor(string memory _name) {
        owner = msg.sender;
        name = _name;
    }

    function proposeOwner(address newOwner) external {
        require(msg.sender == owner, "not owner");
        pendingOwner = newOwner;
    }

    function acceptOwnership() external {
        require(msg.sender == pendingOwner, "not pending owner");
        owner = pendingOwner;
        pendingOwner = address(0);
    }

    function setName(string memory _name) external {
        require(msg.sender == owner, "not owner");
        name = _name;
    }
}
