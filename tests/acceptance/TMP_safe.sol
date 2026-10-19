// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract T {
    uint256 public deadline;

    function claim(address payable to) external {
        require(block.timestamp >= deadline);
        to.transfer(1);
    }
}
