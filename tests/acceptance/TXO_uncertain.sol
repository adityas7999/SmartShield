// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; modifier auth() { if(tx.origin == owner) { _; } } function pay(address payable to) external auth { to.transfer(1); } }
