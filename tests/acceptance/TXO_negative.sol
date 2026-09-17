// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { address owner; event Origin(address a); function viewOrigin() external { emit Origin(tx.origin); } function equal() external view returns(bool) { return tx.origin == owner; } }
