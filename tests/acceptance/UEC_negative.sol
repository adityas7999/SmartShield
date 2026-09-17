// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
interface I { function call() external; } contract T { function pay(I to) external { to.call(); } }
