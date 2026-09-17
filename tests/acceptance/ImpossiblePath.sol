// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { mapping(address=>uint) b; function f(bool flag) external { require(b[msg.sender]>0); if(flag) { (bool ok,)=msg.sender.call(""); require(ok); } if(!flag) b[msg.sender]=0; } }
