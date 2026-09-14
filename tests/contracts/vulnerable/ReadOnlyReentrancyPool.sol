// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Fixture: REN-UNS-01
// Purpose: A callback can observe inconsistent reserve/share pricing.
contract ReadOnlyReentrancyPool {
    mapping(address => uint256) public shares;
    uint256 public totalShares;
    uint256 public totalReserves;
    bool private entered;

    modifier nonReentrant() {
        require(!entered, "reentrant mutation");
        entered = true;
        _;
        entered = false;
    }

    function addLiquidity() external payable nonReentrant {
        shares[msg.sender] += msg.value;
        totalShares += msg.value;
        totalReserves += msg.value;
    }

    function removeLiquidity(uint256 shareAmount) external nonReentrant {
        require(shareAmount > 0 && shares[msg.sender] >= shareAmount, "Invalid shares");
        uint256 payout = (shareAmount * totalReserves) / totalShares;
        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        (bool sent, ) = msg.sender.call{value: payout}("");
        require(sent, "Payout failed");
        totalReserves -= payout;
    }

    function getPricePerShare() external view returns (uint256) {
        if (totalShares == 0) return 1e18;
        return (totalReserves * 1e18) / totalShares;
    }
}
