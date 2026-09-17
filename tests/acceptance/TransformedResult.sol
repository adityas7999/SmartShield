// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function f(address to) external { (bool ok,)=to.call(""); bool success=(ok==true); require(success); } }
