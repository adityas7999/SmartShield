// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Purpose-built training/coverage examples, never independent project evidence.
interface NamedCall { function call(bytes calldata data) external; }
contract Handling {
    uint256 public failures;
    event Failed(address target);

    function discarded(address target, bytes calldata data) external {
        target.call(data);
    }
    function boundUnused(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
    }
    function required(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        require(ok);
    }
    function asserted(address target, bytes calldata data) external {
        (bool ok,) = target.staticcall(data);
        assert(ok);
    }
    function revertFailure(address target, bytes calldata data) external {
        (bool ok,) = target.delegatecall(data);
        if (!ok) revert();
    }
    function recordFailure(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        if (!ok) failures += 1;
    }
    function logFailure(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        if (!ok) emit Failed(target);
    }
    function emptyFailure(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        if (!ok) {}
    }
    function ineffectiveFailure(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        if (!ok) { uint256 unused = 1; }
    }
    function overwritten(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        ok = true;
        require(ok);
    }
    function checkedAlias(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        bool aliasOk = ok;
        require(aliasOk);
    }
    function ignoredAlias(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        bool aliasOk = ok;
    }
    function returned(address target, bytes calldata data) external returns (bool) {
        (bool ok,) = target.call(data);
        return ok;
    }
    function escaped(address target, bytes calldata data) external {
        (bool ok,) = target.call(data);
        consume(ok);
    }
    function consume(bool) private pure {}
    function tupleAssignment(address target, bytes calldata data) external {
        bool ok;
        (ok,) = target.call(data);
        require(ok);
    }
    function looped(address target, bytes calldata data, uint256 count) external {
        for (uint256 i; i < count; ++i) target.call(data);
    }
    function discardDelegate(address target, bytes calldata data) external {
        target.delegatecall(data);
    }
    function discardStatic(address target, bytes calldata data) external view {
        target.staticcall(data);
    }
    function highLevel(NamedCall target, bytes calldata data) external {
        target.call(data);
    }
    function returnFailure(address target, bytes calldata data) external returns (uint256) {
        (bool ok,) = target.call(data);
        if (!ok) return 0;
        return 1;
    }
}
