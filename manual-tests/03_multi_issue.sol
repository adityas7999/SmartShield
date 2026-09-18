// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Multi {
    address public owner;
    mapping(address => uint256) public balances;

    function replace(address newOwner) external {
        owner = newOwner;
    }

    function withdraw() external {
        require(tx.origin == owner, "not owner");
        require(balances[msg.sender] > 0, "no balance");

        (bool ok, ) = msg.sender.call("");
        require(ok, "call failed");

        balances[msg.sender] = 0;
    }
}
