// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-vulnerability reentrancy
/// @custom-expected benign
/// @custom-location balance decrement precedes call; later write is unrelated
contract UnrelatedStateVault {
    mapping(address => uint256) public balances;
    uint256 public lastWithdrawalAmount;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
        lastWithdrawalAmount = amount;
    }
}
