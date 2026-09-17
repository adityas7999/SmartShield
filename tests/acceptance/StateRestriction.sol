// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {address owner;mapping(address=>bool) authorized;function f(address n) external {require(authorized[msg.sender]);owner=n;}}
