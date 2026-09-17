// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function f(address to) external { (bool ok,)=to.call(""); ok=true; require(ok); } }
