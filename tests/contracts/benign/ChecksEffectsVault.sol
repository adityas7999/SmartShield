// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// @custom-id REN-SAF-01
// @custom-vulnerability reentrancy
// @custom-expected benign
// @custom-location line 17
// @custom-reasoning State variable balances[msg.sender] is decremented before the external call, strictly satisfying the Checks-Effects-Interactions pattern.
// @custom-reference Solidity Patterns / Checks-Effects-Interactions
// @custom-reviewer Aayush
contract ChecksEffectsVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
    }
}
