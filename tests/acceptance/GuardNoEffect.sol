// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; function f() external view { require(tx.origin==owner); } }
