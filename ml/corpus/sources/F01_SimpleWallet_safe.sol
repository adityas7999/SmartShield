// SPDX-License-Identifier: MIT
// Family: F01 — SimpleWallet (safe variant)
// Pattern: msg.sender used correctly for withdraw authorization
// Expected: TXO-001 negative, ACC-001 negative, REN-001 negative, UEC-001 negative (failure checked)
pragma solidity ^0.8.20;

contract SimpleWalletSafe {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function deposit() external payable {}

    function withdraw(uint256 amount) external {
        require(msg.sender == owner, "not owner");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
