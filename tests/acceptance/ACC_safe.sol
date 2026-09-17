// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; modifier auth(){require(msg.sender==owner);_;} function set(address n) external auth { owner=n; } }
