// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-id REN-NEG-01
/// @custom-vulnerability reentrancy
/// @custom-expected benign
/// @custom-location line 33
/// @custom-reasoning Although state mutation follows the external call, the function is protected by an explicit mutex lock (nonReentrant modifier) preventing reentrant callbacks.
/// @custom-reference OpenZeppelin ReentrancyGuard
/// @custom-reviewer Aayush
contract GuardedReentrantVault {
    mapping(address => uint256) public balances;
    uint256 private _status;

    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "insufficient");
        (bool sent, ) = payable(msg.sender).call{value: amount}("");
        require(sent, "send failed");
        balances[msg.sender] -= amount;
    }
}

