// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title Minimal Soulbound NFT Interface (EIP-5192)
 * @dev See https://eips.ethereum.org/EIPS/eip-5192
 */
interface IERC5192 {
    /**
     * @notice Emitted when the locking status is changed to locked.
     * @dev If a token is minted and the status is locked, this event should be emitted.
     * @param tokenId The identifier for a token.
     */
    event Locked(uint256 tokenId);

    /**
     * @notice Emitted when the locking status is changed to unlocked.
     * @dev If a token is minted and the status is unlocked, this event should be emitted.
     * @param tokenId The identifier for a token.
     */
    event Unlocked(uint256 tokenId);

    /**
     * @notice Returns the locking status of an Soulbound Token
     * @dev SBTs assigned to zero address are considered invalid, and queries
     * about them do throw.
     * @param tokenId The identifier for an SBT.
     */
    function locked(uint256 tokenId) external view returns (bool);
}

/**
 * @title CredonBadge ($CRED)
 * @notice The soulbound (non-transferable) governance token of the Credon Protocol ecosystem.
 * Implements EIP-5192.
 */
contract CredonBadge is ERC721, AccessControl, IERC5192 {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    // EIP-5192 interface ID
    bytes4 private constant INTERFACE_ID_ERC5192 = 0xb45a3c0e;

    error TransferNotAllowed();
    error InvalidTokenId();

    /**
     * @notice Initializes the CredonBadge contract.
     * @param defaultAdmin The address granted the DEFAULT_ADMIN_ROLE.
     */
    constructor(address defaultAdmin) ERC721("CredonBadge", "CRED") {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
    }

    /**
     * @notice See {IERC165-supportsInterface}.
     */
    function supportsInterface(bytes4 interfaceId) public view virtual override(ERC721, AccessControl) returns (bool) {
        return interfaceId == INTERFACE_ID_ERC5192 || super.supportsInterface(interfaceId);
    }

    /**
     * @notice Returns true to indicate the token is permanently locked.
     * @param tokenId The identifier for the token.
     * @return bool Returns true unconditionally.
     */
    function locked(uint256 tokenId) external view override returns (bool) {
        // According to EIP-5192: "SBTs assigned to zero address are considered invalid, and queries about them do throw."
        if (_ownerOf(tokenId) == address(0)) {
            revert InvalidTokenId();
        }
        return true;
    }

    /**
     * @notice Mints a new $CRED badge.
     * @dev Only callable by an account with the MINTER_ROLE. Emits the Locked event from EIP-5192.
     * @param to The address to receive the minted badge.
     * @param tokenId The unique identifier for the badge.
     */
    function mint(address to, uint256 tokenId) external onlyRole(MINTER_ROLE) {
        _mint(to, tokenId);
        emit Locked(tokenId);
    }

    /**
     * @notice Hook that is called before any token transfer. This includes minting and burning.
     * @dev Reverts if the transfer is not a mint or burn, enforcing the soulbound property.
     */
    function _update(address to, uint256 tokenId, address auth) internal virtual override returns (address) {
        address from = _ownerOf(tokenId);
        // If from != address(0) && to != address(0), this is a normal transfer
        if (from != address(0) && to != address(0)) {
            revert TransferNotAllowed();
        }
        return super._update(to, tokenId, auth);
    }
}
