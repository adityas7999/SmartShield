// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address admin; function set(address n,bool enabled) external { if(enabled) admin=n; } }
