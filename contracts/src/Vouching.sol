// SPDX-License-Identifier: MIT
pragma solidity 0.8.27;

import {IERC20} from "openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "openzeppelin-contracts/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "openzeppelin-contracts/contracts/access/Ownable.sol";

/// @title Vouching 2.0 Bonded Endorsement Scaffold
/// @dev A basic implementation of the Vouching 2.0 mechanism where users can bond tokens to endorse others.
contract Vouching is Ownable {
    using SafeERC20 for IERC20;

    IERC20 public immutable CRE_TOKEN;
    uint256 public constant PROBATION_PERIOD = 180 days;
    address public treasury;

    struct Bond {
        uint256 amount;
        uint256 lockedUntil;
        bool isActive;
    }

    // voucher => vouchee => Bond
    mapping(address => mapping(address => Bond)) public bonds;

    event BondPlaced(address indexed voucher, address indexed vouchee, uint256 amount, uint256 lockedUntil);
    event BondWithdrawn(address indexed voucher, address indexed vouchee, uint256 amount);
    event BondSlashed(address indexed voucher, address indexed vouchee, uint256 amount, address treasury);
    event TreasuryUpdated(address oldTreasury, address newTreasury);

    error InvalidAddress();
    error InvalidAmount();
    error BondAlreadyExists();
    error BondNotActive();
    error BondStillLocked();
    error CannotVouchSelf();

    constructor(address creToken_, address initialOwner, address initialTreasury) Ownable(initialOwner) {
        if (creToken_ == address(0) || initialOwner == address(0) || initialTreasury == address(0)) {
            revert InvalidAddress();
        }
        CRE_TOKEN = IERC20(creToken_);
        treasury = initialTreasury;
    }

    /// @notice Updates the treasury address where slashed funds are sent
    /// @param newTreasury The address of the new treasury
    function setTreasury(address newTreasury) external onlyOwner {
        if (newTreasury == address(0)) revert InvalidAddress();
        address oldTreasury = treasury;
        treasury = newTreasury;
        emit TreasuryUpdated(oldTreasury, newTreasury);
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

        delete bonds[msg.sender][vouchee];

        CRE_TOKEN.safeTransfer(msg.sender, amount);

        emit BondWithdrawn(msg.sender, vouchee, amount);
    }

    /// @notice Slashes a bond (e.g., if the vouchee acts maliciously).
    /// @dev Restricted to the contract owner (governance).
    /// @param voucher The address that placed the bond
    /// @param vouchee The address that was endorsed
    function slashBond(address voucher, address vouchee) external onlyOwner {
        Bond storage currentBond = bonds[voucher][vouchee];
        if (!currentBond.isActive) revert BondNotActive();

        uint256 amount = currentBond.amount;
        address currentTreasury = treasury;

        delete bonds[voucher][vouchee];

        CRE_TOKEN.safeTransfer(currentTreasury, amount);

        emit BondSlashed(voucher, vouchee, amount, currentTreasury);
    }
}
