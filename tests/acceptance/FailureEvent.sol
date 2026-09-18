// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T {
    event Failed();
    function f(address to) external {
        (bool ok, ) = to.call("");
        if (!ok) emit Failed();
    }
}
