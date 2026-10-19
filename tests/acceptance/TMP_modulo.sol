// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract T {
    function roll(address payable to) external {
        uint256 winner = block.timestamp % 2;
        if (winner == 0) {
            to.transfer(1);
        }
    }
}
