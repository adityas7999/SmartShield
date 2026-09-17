// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address admin; function f(address n) external { assert(msg.sender==admin); admin=n; } }
