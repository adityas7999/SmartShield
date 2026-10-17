// SPDX-License-Identifier: MIT
// Family: F07 — ProxyRouter (safe variant)
// Pattern: Upgradeable proxy with proper auth and checked delegatecall
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract ProxyRouterSafe {
    address public owner;
    address public implementation;

    constructor(address impl) {
        owner = msg.sender;
        implementation = impl;
    }

    function setImplementation(address newImpl) external {
        require(msg.sender == owner, "not owner");
        implementation = newImpl;
    }

    function dispatch(bytes calldata data) external payable {
        (bool ok, ) = implementation.delegatecall(data);
        require(ok, "delegatecall failed");
    }

    function transferOwner(address newOwner) external {
        require(msg.sender == owner, "not owner");
        owner = newOwner;
    }
}
