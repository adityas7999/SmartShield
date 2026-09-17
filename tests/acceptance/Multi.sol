// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Multi { address public owner; mapping(address=>uint) balances; function replace(address n) external { owner=n; } function withdraw() external { require(tx.origin==owner); require(balances[msg.sender]>0); msg.sender.call(""); balances[msg.sender]=0; } }
