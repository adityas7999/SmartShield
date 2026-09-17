// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; function check() internal view { require(msg.sender==owner); } function f(address n) external {check();owner=n;} }
