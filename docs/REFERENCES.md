# SmartShield Security References

These sources support the security semantics used in the detector specification. The project should review the sources directly before final approval.

## Solidity documentation

- Solidity security considerations, including `tx.origin` authorization guidance:
  https://docs.soliditylang.org/en/latest/security-considerations.html
- Solidity security considerations, including reentrancy and checks-effects-interactions:
  https://docs.soliditylang.org/en/latest/security-considerations.html#reentrancy
- Solidity units and global variables, including `msg.sender` and `tx.origin`:
  https://docs.soliditylang.org/en/latest/units-and-global-variables.html
- Solidity address members and low-level calls:
  https://docs.soliditylang.org/en/latest/types.html#members-of-addresses

## Review note

These references explain the underlying language and security concepts. They do not prove that a particular SmartShield finding is exploitable. Detector output must remain evidence-based and must include limitations for unresolved calls, unsupported constructs, and incomplete interprocedural reasoning.
