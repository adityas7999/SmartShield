// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { mapping(address=>uint) b; function pay() external { require(b[msg.sender]>0); b[msg.sender]=0; (bool ok,)=msg.sender.call(""); require(ok); } }
