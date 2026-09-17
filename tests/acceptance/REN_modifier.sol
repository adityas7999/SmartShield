// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { uint status; mapping(address=>uint) b; modifier lock(){require(status==0);status=1;_;status=0;} function f() external lock {require(b[msg.sender]>0); (bool ok,)=msg.sender.call("");require(ok);b[msg.sender]=0;} }
