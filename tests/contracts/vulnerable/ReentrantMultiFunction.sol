// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-id REN-VAR-01
/// @custom-vulnerability reentrancy
/// @custom-expected vulnerable
/// @custom-location line 28
/// @custom-reasoning withdrawAll() triggers an external call to msg.sender before zeroing user balance. The recipient can reenter via transferTo(), which reads the unzeroed balance to double-spend.
/// @custom-reference SWC-107 / Cross-Function Reentrancy
/// @custom-reviewer Aayush
contract ReentrantMultiFunction {
    mapping(address => uint256) public userBalances;

    function deposit() external payable {
        userBalances[msg.sender] += msg.value;
    }

    function withdrawAll() external {
        uint256 balance = userBalances[msg.sender];
        require(balance > 0, "No balance");

        (bool success, ) = payable(msg.sender).call{value: balance}("");
        require(success, "Transfer failed");

        userBalances[msg.sender] = 0;
    }

    function transferTo(address recipient, uint256 amount) external {
        require(userBalances[msg.sender] >= amount, "Insufficient balance");
        userBalances[msg.sender] -= amount;
        userBalances[recipient] += amount;
    }
}

