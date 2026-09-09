// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// @custom-id TXO-UNS-01
// @custom-vulnerability tx-origin-authorization
// @custom-expected unsupported
// @custom-location line 33
// @custom-reasoning Authorization is delegated to an internal library method checking tx.origin. The Sprint 1 Call Graph and intra-contract CFG do not follow external library delegation, marking this as an expected analysis limitation.
// @custom-reference SmartShield Detector Specification Section 12 Limitations
// @custom-reviewer Aditya
library OriginAuthLib {
    function isOriginOwner(address owner) internal view returns (bool) {
        return tx.origin == owner;
    }
}

contract TxOriginIndirectLibrary {
    using OriginAuthLib for address;
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function transferPrivileged(address payable recipient, uint256 amount) external {
        require(owner.isOriginOwner(), "Origin check failed via library");
        recipient.transfer(amount);
    }

    receive() external payable {}
}
