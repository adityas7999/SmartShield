// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract T { function pay(address to) external { bool ok; (ok,)=to.call(""); bool success=ok; require(success); } }
