// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract T {
    uint256 public count;

    function f(uint256 n) external {
        count = n;
    }
}
