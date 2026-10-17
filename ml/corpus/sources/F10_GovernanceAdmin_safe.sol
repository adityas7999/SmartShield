// SPDX-License-Identifier: MIT
// Family: F10 — GovernanceAdmin (safe variant)
// Pattern: Restricted admin replacement requiring caller to be current admin
pragma solidity ^0.8.20;

contract GovernanceAdminSafe {
    address public admin;
    uint256 public proposalCount;

    constructor() {
        admin = msg.sender;
    }

    function setAdmin(address newAdmin) external {
        require(msg.sender == admin, "not admin");
        admin = newAdmin;
    }

    function createProposal() external {
        proposalCount++;
    }
}
