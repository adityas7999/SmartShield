// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function pay(address to) external returns(bool) { (bool ok,)=to.call(""); return ok; } }
