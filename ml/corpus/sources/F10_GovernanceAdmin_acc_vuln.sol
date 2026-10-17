// SPDX-License-Identifier: MIT
// Family: F10 — GovernanceAdmin
// Pattern: Unrestricted admin replacement without authorization
pragma solidity ^0.8.20;

contract GovernanceAdminVuln {
    address public admin;
    uint256 public proposalCount;

    constructor() {
        admin = msg.sender;
    }

    // ACC-001: replaces designated admin without authorization
    function setAdmin(address newAdmin) external {
        admin = newAdmin;
    }

    function createProposal() external {
        proposalCount++;
    }
}
