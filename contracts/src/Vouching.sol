// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {IERC20} from "openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "openzeppelin-contracts/contracts/token/ERC20/utils/SafeERC20.sol";

/// @title Vouching 2.0 Bonded Endorsement Scaffold
/// @dev A basic implementation of the Vouching 2.0 mechanism where users can bond tokens to endorse others.
contract Vouching {
    using SafeERC20 for IERC20;

    IERC20 public immutable CRE_TOKEN;
    uint256 public constant PROBATION_PERIOD = 180 days;

    struct Bond {
        uint256 amount;
        uint256 lockedUntil;
        bool isActive;
    }

    // voucher => vouchee => Bond
    mapping(address => mapping(address => Bond)) public bonds;

    event BondPlaced(address indexed voucher, address indexed vouchee, uint256 amount, uint256 lockedUntil);
    event BondWithdrawn(address indexed voucher, address indexed vouchee, uint256 amount);
    event BondSlashed(address indexed voucher, address indexed vouchee, uint256 amount);

    error InvalidAmount();
    error BondAlreadyExists();
    error BondNotActive();
    error BondStillLocked();
    error CannotVouchSelf();

    constructor(address creToken_) {
        CRE_TOKEN = IERC20(creToken_);
    }

    /// @notice Places a bonded endorsement for a target address
    /// @param vouchee The address being endorsed
    /// @param amount The amount of CRE tokens to lock as a bond
    function placeBond(address vouchee, uint256 amount) external {
        if (amount == 0) revert InvalidAmount();
        if (msg.sender == vouchee) revert CannotVouchSelf();

        Bond storage currentBond = bonds[msg.sender][vouchee];
        if (currentBond.isActive) revert BondAlreadyExists();

        uint256 unlockTime = block.timestamp + PROBATION_PERIOD;

        currentBond.amount = amount;
        currentBond.lockedUntil = unlockTime;
        currentBond.isActive = true;

        CRE_TOKEN.safeTransferFrom(msg.sender, address(this), amount);

        emit BondPlaced(msg.sender, vouchee, amount, unlockTime);
    }

    /// @notice Withdraws a previously placed bond after the probation period expires
    /// @param vouchee The address that was endorsed
    function withdrawBond(address vouchee) external {
        Bond storage currentBond = bonds[msg.sender][vouchee];

        if (!currentBond.isActive) revert BondNotActive();
        if (block.timestamp < currentBond.lockedUntil) revert BondStillLocked();

        uint256 amount = currentBond.amount;

        currentBond.isActive = false;
        currentBond.amount = 0;

        CRE_TOKEN.safeTransfer(msg.sender, amount);

        emit BondWithdrawn(msg.sender, vouchee, amount);
    }

    /// @notice Slashes a bond (e.g., if the vouchee acts maliciously).
    /// @dev In a full implementation, this would be restricted to a governance or ZK verifier role.
    /// @param voucher The address that placed the bond
    /// @param vouchee The address that was endorsed
    function slashBond(address voucher, address vouchee) external {
        Bond storage currentBond = bonds[voucher][vouchee];
        if (!currentBond.isActive) revert BondNotActive();

        uint256 amount = currentBond.amount;

        currentBond.isActive = false;
        currentBond.amount = 0;

        // For scaffold purposes, we just burn the slashed tokens (or send to a treasury)
        // Here we'll just transfer to the zero address / burn it
        CRE_TOKEN.safeTransfer(address(0xdEaD), amount);

        emit BondSlashed(voucher, vouchee, amount);
    }
}
