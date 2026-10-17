// SPDX-License-Identifier: MIT
// Family: F06 — TokenVesting
// Pattern: Time-locked token vesting with CEI — safe across all rules
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative
pragma solidity ^0.8.20;

contract TokenVesting {
    address public owner;
    address public beneficiary;
    uint256 public vestingEnd;
    uint256 public totalAmount;
    uint256 public released;

    constructor(address _beneficiary, uint256 durationSeconds) payable {
        owner = msg.sender;
        beneficiary = _beneficiary;
        vestingEnd = block.timestamp + durationSeconds;
        totalAmount = msg.value;
    }

    function releasable() public view returns (uint256) {
        if (block.timestamp < vestingEnd) return 0;
        return totalAmount - released;
    }

    function release() external {
        require(msg.sender == beneficiary, "not beneficiary");
        uint256 amount = releasable();
        require(amount > 0, "nothing to release");
        released += amount;  // state update before transfer
        (bool ok, ) = beneficiary.call{value: amount}("");
        require(ok, "transfer failed");
    }

    function revoke() external {
        require(msg.sender == owner, "not owner");
        require(block.timestamp < vestingEnd, "vesting ended");
        uint256 remaining = address(this).balance;
        (bool ok, ) = owner.call{value: remaining}("");
        require(ok, "revoke failed");
    }
}
