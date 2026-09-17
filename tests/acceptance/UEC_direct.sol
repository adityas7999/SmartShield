// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function pay(address to) external { to.call(""); } }
