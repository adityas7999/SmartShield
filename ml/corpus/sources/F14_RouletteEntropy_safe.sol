// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Family: F14-RouletteEntropy
// Variant: Safe against TMP-001 (Uses commit-reveal hash seed rather than direct timestamp modulo)
// Expected: TXO-001 negative, REN-001 negative, ACC-001 negative, UEC-001 negative, TMP-001 negative

contract RouletteEntropySafe {
    address public croupier;
    uint256 public roundId;
    address public lastWinner;
    bytes32 public secretCommit;

    event RoundResolved(uint256 indexed round, address winner, uint256 outcome);

    constructor(bytes32 _commit) {
        croupier = msg.sender;
        secretCommit = _commit;
    }

    function spinWheel(address payable playerA, address payable playerB, uint256 secret) external {
        require(msg.sender == croupier, "unauthorized croupier");
        require(keccak256(abi.encodePacked(secret)) == secretCommit, "invalid reveal");

        // Safe: entropy derived from reveal secret and previous blockhash
        uint256 outcome = uint256(keccak256(abi.encodePacked(blockhash(block.number - 1), secret))) % 2;
        address payable chosenWinner = (outcome == 0) ? playerA : playerB;

        lastWinner = chosenWinner;
        roundId += 1;

        chosenWinner.transfer(0.5 ether);
        emit RoundResolved(roundId, chosenWinner, outcome);
    }
}
