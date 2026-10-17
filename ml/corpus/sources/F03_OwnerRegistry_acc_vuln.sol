// SPDX-License-Identifier: MIT
// Family: F03 — OwnerRegistry
// Pattern: Public function replaces owner without any authorization guard
// Expected: TXO-001 negative, REN-001 negative, ACC-001 positive, UEC-001 negative
pragma solidity ^0.8.20;

contract OwnerRegistry {
    address public owner;
    address public admin;
    string public name;

    constructor(string memory _name) {
        owner = msg.sender;
        admin = msg.sender;
        name = _name;
    }

    // ACC-001: replaces 'owner' with no msg.sender == owner restriction
    function transferOwnership(address newOwner) external {
        owner = newOwner;
    }

    // ACC-001: replaces 'admin' with no restriction
    function setAdmin(address newAdmin) external {
        admin = newAdmin;
    }

    function setName(string memory _name) external {
        require(msg.sender == owner, "not owner");
        name = _name;
    }
}
