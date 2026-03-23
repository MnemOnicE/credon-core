// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity >=0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title CredonToken ($CRE)
 * @notice The utility token of the Credon Protocol ecosystem.
 */
contract CredonToken is ERC20, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    /**
     * @notice Initializes the CredonToken contract.
     * @param defaultAdmin The address granted the DEFAULT_ADMIN_ROLE.
     */
    constructor(address defaultAdmin) ERC20("CredonToken", "CRE") {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
    }

    /**
     * @notice Mints new $CRE tokens.
     * @dev Only callable by an account with the MINTER_ROLE (e.g., RewardsReservoir).
     * @param to The address to receive the minted tokens.
     * @param amount The amount of tokens to mint.
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }
}
