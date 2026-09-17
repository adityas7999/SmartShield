// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { struct S {uint b;} mapping(address=>S) data; function f() external {S storage s=data[msg.sender];require(s.b>0);(bool ok,)=msg.sender.call("");require(ok);s.b=0;} }
