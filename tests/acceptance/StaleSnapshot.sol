// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {mapping(uint=>uint) b;function f(address to) external {uint n=b[1];b[1]=0;require(n>0);(bool ok,)=to.call("");require(ok);b[1]=1;}}
