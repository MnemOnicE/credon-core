// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity 0.8.27;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {CredonToken} from "./CredonToken.sol";

/**
 * @title RewardsReservoir
 * @notice A time-locked treasury contract that authorizes the minting of $CRE tokens.
 * It gates the minting based on ZK-Rollup state updates and enforces a maximum
 * emission rate per time period (epoch).
 */
contract RewardsReservoir is AccessControl {
    bytes32 public constant ZK_PROVER_ROLE = keccak256("ZK_PROVER_ROLE");

    CredonToken public immutable CREDON_TOKEN;

    // A mapping to track if a specific zk-proof or state update ID has already been claimed
    mapping(bytes32 => bool) public processedStateUpdates;

    // Time-lock and emission rate limit state variables
    uint256 public constant EPOCH_DURATION = 1 days;
    uint256 public maxTokensPerEpoch;

    uint256 public currentEpochStartTime;
    uint256 public tokensMintedThisEpoch;

    event StateUpdated(bytes32 indexed updateId, address indexed to, uint256 amount);
    event EmissionRateUpdated(uint256 newMaxTokensPerEpoch);

    error UpdateAlreadyProcessed();
    error EmissionLimitExceeded(uint256 requested, uint256 available);

    /**
     * @notice Initializes the RewardsReservoir.
     * @param defaultAdmin Address to receive DEFAULT_ADMIN_ROLE.
     * @param _credonToken Address of the CredonToken contract.
     * @param _initialMaxTokensPerEpoch The maximum amount of $CRE that can be minted per epoch (1 day).
     */
    constructor(address defaultAdmin, address _credonToken, uint256 _initialMaxTokensPerEpoch) {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        CREDON_TOKEN = CredonToken(_credonToken);
        maxTokensPerEpoch = _initialMaxTokensPerEpoch;
        currentEpochStartTime = block.timestamp;
    }

    /**
     * @notice Updates the maximum emission rate per epoch.
     * @dev Only callable by the DEFAULT_ADMIN_ROLE.
     * @param _newMaxTokensPerEpoch The new limit.
     */
    function setMaxTokensPerEpoch(uint256 _newMaxTokensPerEpoch) external onlyRole(DEFAULT_ADMIN_ROLE) {
        maxTokensPerEpoch = _newMaxTokensPerEpoch;
        emit EmissionRateUpdated(_newMaxTokensPerEpoch);
    }

    /**
     * @notice Authorizes the minting of $CRE based on mathematically proven off-chain TrustScore updates.
     * @dev Only callable by an account with the ZK_PROVER_ROLE. Enforces time-lock/rate-limit.
     * @param updateId Unique identifier for the state update (e.g., SMT root or proof hash) to prevent replay.
     * @param to The recipient of the minted tokens.
     * @param amount The amount of $CRE to mint.
     */
    function authorizeClaim(bytes32 updateId, address to, uint256 amount) external onlyRole(ZK_PROVER_ROLE) {
        if (processedStateUpdates[updateId]) {
            revert UpdateAlreadyProcessed();
        }

        // Check and reset epoch if necessary
        if (block.timestamp >= currentEpochStartTime + EPOCH_DURATION) {
            currentEpochStartTime = block.timestamp;
            tokensMintedThisEpoch = 0;
        }

        // Check emission rate limit
        uint256 availableToMint = maxTokensPerEpoch - tokensMintedThisEpoch;
        if (amount > availableToMint) {
            revert EmissionLimitExceeded(amount, availableToMint);
        }

        processedStateUpdates[updateId] = true;
        tokensMintedThisEpoch += amount;

        CREDON_TOKEN.mint(to, amount);

        emit StateUpdated(updateId, to, amount);
    }
}
