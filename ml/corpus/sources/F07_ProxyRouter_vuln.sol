// SPDX-License-Identifier: MIT
// Family: F07 — ProxyRouter
// Pattern: Upgradeable proxy with delegatecall result unchecked and owner replaceable
// Expected: TXO-001 negative, REN-001 negative, ACC-001 positive, UEC-001 positive (delegatecall high)
pragma solidity ^0.8.20;

contract ProxyRouter {
    address public owner;
    address public implementation;

    constructor(address impl) {
        owner = msg.sender;
        implementation = impl;
    }

    // ACC-001: 'implementation' is used in delegatecall — it is a security-critical address.
    // No restriction on who can call setImplementation.
    function setImplementation(address newImpl) external {
        implementation = newImpl;
    }

    // UEC-001 (high): delegatecall result discarded
    function dispatch(bytes calldata data) external payable {
        implementation.delegatecall(data);
    }

    // ACC-001: replaces owner without restriction
    function transferOwner(address newOwner) external {
        owner = newOwner;
    }
}
