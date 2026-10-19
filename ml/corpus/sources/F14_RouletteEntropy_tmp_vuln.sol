// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Family: F14-RouletteEntropy
// Variant: Vulnerable to TMP-001 (Timestamp used as pseudo-random entropy modulo)
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative, TMP-001 positive

contract RouletteEntropy {
    address public croupier;
    uint256 public roundId;
    address public lastWinner;

    event RoundResolved(uint256 indexed round, address winner, uint256 outcome);

    constructor() {
        croupier = msg.sender;
    }

    function spinWheel(address payable playerA, address payable playerB) external {
        require(msg.sender == croupier, "unauthorized croupier");

        // TMP-001: Modulo arithmetic on block.timestamp as random seed
        uint256 outcome = block.timestamp % 2;
        address payable chosenWinner = (outcome == 0) ? playerA : playerB;

        lastWinner = chosenWinner;
        roundId += 1;

        chosenWinner.transfer(0.5 ether);
        emit RoundResolved(roundId, chosenWinner, outcome);
    }
}
