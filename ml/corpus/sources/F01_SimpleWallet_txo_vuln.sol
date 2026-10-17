// SPDX-License-Identifier: MIT
// Family: F01 — SimpleWallet
// Pattern: tx.origin used as sole caller identity for withdraw authorization
// Expected: TXO-001 positive, ACC-001 negative (no authority replacement), REN-001 negative, UEC-001 positive (unchecked call)
pragma solidity ^0.8.20;

contract SimpleWallet {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {}

    event Withdrawn(address indexed to, uint256 amount, bool success);

    function withdraw(uint256 amount) external {
        require(tx.origin == owner, "not owner");
        // UEC-001: result bound to ok and emitted — but never checked via require/assert
        // Normal continuation reached without failure handling
        (bool ok, ) = msg.sender.call{value: amount}("");
        emit Withdrawn(msg.sender, amount, ok);
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
