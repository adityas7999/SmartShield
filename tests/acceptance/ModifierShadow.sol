// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {address owner; address admin; modifier auth(){require(msg.sender==owner);_;} function f(address owner,address n) external auth {owner;admin=n;}}
