// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract Base { address internal owner; modifier auth(){require(msg.sender==owner);_;} } contract T is Base { function set(address n) external auth { owner=n; } }
