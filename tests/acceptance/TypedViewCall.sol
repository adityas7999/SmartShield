// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
interface I {function read() external view returns(uint);} contract T {uint b;function f(I to) external {require(b>0);to.read();b=0;}}
