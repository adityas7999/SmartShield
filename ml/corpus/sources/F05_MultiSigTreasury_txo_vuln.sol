// SPDX-License-Identifier: MIT
// Family: F05 — MultiSigTreasury (tx.origin variant)
// Pattern: tx.origin used instead of msg.sender for cosigner check
// Expected: TXO-001 positive, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract MultiSigTreasuryTxOrigin {
    address public owner;
    mapping(bytes32 => bool) public executed;

    constructor() {
        owner = msg.sender;
    }

    // TXO-001: tx.origin used for authorization of state-changing operation
    function execute(
        address target,
        uint256 value,
        bytes calldata data,
        bytes32 txHash
    ) external {
        require(tx.origin == owner, "not authorized");
        require(!executed[txHash], "already executed");
        executed[txHash] = true;
        (bool ok, ) = target.call{value: value}(data);
        require(ok, "execution failed");
    }

    receive() external payable {}
}
