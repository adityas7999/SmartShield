// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function f(address a,address b) external { a.call(""); b.call(""); } }
