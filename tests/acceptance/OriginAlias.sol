// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; function f(address payable to) external {address origin=tx.origin; require(origin==owner);to.transfer(1);} }
