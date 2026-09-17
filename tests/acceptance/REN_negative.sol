// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { mapping(uint=>uint) b; function pay(address to) external { require(b[1]>0); (bool ok,)=to.call(""); require(ok); b[2]=0; } }
