// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {address owner;function f(address n) external {owner=n;require(msg.sender==owner);owner=address(1);}}
