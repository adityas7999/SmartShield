// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { mapping(uint=>uint) b; function pay(address to) external { uint amount=b[1]; require(amount>0); (bool ok,)=to.call(""); require(ok); b[1]=0; } }
