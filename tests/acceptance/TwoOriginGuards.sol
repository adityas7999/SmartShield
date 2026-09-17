// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {address owner; function f(address payable to) external {require(tx.origin==owner);to.transfer(1);} function g(address payable to) external {require(tx.origin==owner);to.transfer(1);} }
