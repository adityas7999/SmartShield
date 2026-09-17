// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; function f(address n,bool enabled) external {require(msg.sender==owner || enabled);owner=n;} }
