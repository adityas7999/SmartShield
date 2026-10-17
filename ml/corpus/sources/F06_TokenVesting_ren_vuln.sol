// SPDX-License-Identifier: MIT
// Family: F06 — TokenVesting (reentrancy variant)
// Pattern: Vesting contract that updates state AFTER external call — reentrancy window
// Expected: TXO-001 negative, REN-001 positive, ACC-001 negative, UEC-001 positive
pragma solidity ^0.8.20;

contract TokenVestingRen {
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

    // REN-001: checks released (via releasable), calls external, THEN updates released
    // UEC-001: call result not checked
    function release() external {
        require(msg.sender == beneficiary, "not beneficiary");
        require(block.timestamp >= vestingEnd, "vesting not ended");
        uint256 amount = totalAmount - released;
        require(amount > 0, "nothing to release");
        beneficiary.call{value: amount}("");   // UEC-001: discarded
        released += amount;                     // REN-001: state update after external call
    }
}
