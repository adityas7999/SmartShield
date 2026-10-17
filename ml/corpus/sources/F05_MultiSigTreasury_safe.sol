// SPDX-License-Identifier: MIT
// Family: F05 — MultiSigTreasury
// Pattern: Well-guarded multi-sig — negative for all four rules
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract MultiSigTreasury {
    address public owner;
    address public cosigner;
    mapping(bytes32 => bool) public executed;

    constructor(address _cosigner) {
        owner = msg.sender;
        cosigner = _cosigner;
    }

    function execute(
        address target,
        uint256 value,
        bytes calldata data,
        bytes32 txHash
    ) external {
        require(msg.sender == owner, "not owner");
        require(!executed[txHash], "already executed");
        executed[txHash] = true;  // CEI: state update before call
        (bool ok, ) = target.call{value: value}(data);
        require(ok, "execution failed");
    }

    function setCosigner(address newCosigner) external {
        require(msg.sender == owner, "not owner");  // ACC: guarded by msg.sender == owner
        cosigner = newCosigner;
    }

    receive() external payable {}
}
