// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {bool status;function f(address to) external {(status,)=to.call("");}}
