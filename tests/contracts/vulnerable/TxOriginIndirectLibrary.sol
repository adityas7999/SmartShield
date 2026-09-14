// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: TXO-UNS-01
// Purpose: See expected-results.json for scope and reasoning.
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
