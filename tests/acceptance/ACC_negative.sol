// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { mapping(address=>uint) balances; uint public counter; function deposit() external payable { balances[msg.sender]+=msg.value; counter=1; } }
