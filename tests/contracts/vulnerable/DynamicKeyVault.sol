// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IReceiver {
    function receiveFunds() external payable;
}

/// @custom-vulnerability reentrancy
/// @custom-expected unresolved
/// @custom-location dynamic key relationship requires reduced confidence
contract DynamicKeyVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(address receiver, bytes calldata encodedKey, uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient");
        IReceiver(receiver).receiveFunds{value: amount}();
        balances[abi.decode(encodedKey, (address))] -= amount;
    }
}
