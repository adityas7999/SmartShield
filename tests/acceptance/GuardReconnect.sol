// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; uint count; function f() external { if(tx.origin==owner) { count; } count=2; } }
