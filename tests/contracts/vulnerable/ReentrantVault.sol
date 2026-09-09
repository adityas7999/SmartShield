// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// @custom-id REN-DIR-01
// @custom-vulnerability reentrancy
// @custom-expected vulnerable
// @custom-location line 17
// @custom-reasoning Low-level external call occurs before balances[msg.sender] is updated. Recipient contract fallback can re-invoke withdraw() repeatedly before state decrement.
// @custom-reference SWC-107 (The DAO pattern)
// @custom-reviewer Aayush
contract ReentrantVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
        balances[msg.sender] -= amount;
    }
}
