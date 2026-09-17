// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; function pay(address payable to) external { if(tx.origin != owner) revert(); to.transfer(1); } }
