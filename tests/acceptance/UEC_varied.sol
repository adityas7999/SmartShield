// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function read(address to) external view { (bool ok,)=to.staticcall(""); ok; } }
