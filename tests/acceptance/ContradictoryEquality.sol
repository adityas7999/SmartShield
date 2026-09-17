// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {address owner;function f(address n,uint x) external {require(x==1);require(x==2);owner=n;}}
