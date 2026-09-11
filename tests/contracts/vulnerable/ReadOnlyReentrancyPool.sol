// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @custom-id REN-UNS-01
/// @custom-vulnerability reentrancy
/// @custom-expected unsupported
/// @custom-location line 34
/// @custom-reasoning Read-only reentrancy where removeLiquidity sends an external callback while totalShares and reserves are temporarily inconsistent. getPricePerShare() is a view function with no post-call state write, making single-contract intra-procedural CFG unable to detect it without cross-contract oracle modeling.
/// @custom-reference Curve LP / Sentiment Read-Only Reentrancy exploits (2023)
/// @custom-reviewer Aayush
contract ReadOnlyReentrancyPool {
    uint256 public totalShares;
    uint256 public totalReserves;

    function addLiquidity() external payable {
        totalShares += msg.value;
        totalReserves += msg.value;
    }

    function removeLiquidity(uint256 shareAmount) external {
        require(totalShares >= shareAmount, "Excessive shares");

        uint256 payout = (shareAmount * totalReserves) / totalShares;
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

