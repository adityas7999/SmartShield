// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {bool entered; mapping(address=>uint) b; modifier lock(){require(!entered);entered=true;_;entered=false;} function f() external lock {require(b[msg.sender]>0);(bool ok,)=msg.sender.call("");require(ok);b[msg.sender]=0;} }
