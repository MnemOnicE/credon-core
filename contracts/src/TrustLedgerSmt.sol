// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity 0.8.27;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {SmtLib} from "@iden3/contracts/lib/SmtLib.sol";
import {PoseidonUnit2L, PoseidonUnit3L} from "@iden3/contracts/lib/Poseidon.sol";

/**
 * @title TrustLedgerSmt
 * @notice Receives and verifies a single 32-byte SMT root hash per recalculation epoch.
 * Integrates optimized inclusion proof verification for user real-time state authentication.
 */
contract TrustLedgerSmt is AccessControl {
    using SmtLib for SmtLib.Data;

    bytes32 public constant ZK_PROVER_ROLE = keccak256("ZK_PROVER_ROLE");

    SmtLib.Data internal smt;

    // The current global TrustScore SMT root hash
    bytes32 public currentRoot;

    // Tracks historical roots to allow verification of slightly older states if needed
    mapping(bytes32 => bool) public historicalRoots;

    event RootUpdated(bytes32 indexed oldRoot, bytes32 indexed newRoot, uint256 timestamp);

    error Unauthorized();
    error RootAlreadyExists();
    error InvalidProof();

    constructor(address defaultAdmin) {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        smt.initialize(64); // Initialize SMT with max depth of 64
    }

    /**
     * @notice Updates the global TrustScore SMT root hash.
     * @dev Only callable by the ZK_PROVER_ROLE (the off-chain sequencer).
     * @param newRoot The new 32-byte SMT root hash.
     */
    function updateRoot(bytes32 newRoot) external onlyRole(ZK_PROVER_ROLE) {
        if (historicalRoots[newRoot]) revert RootAlreadyExists();

        bytes32 oldRoot = currentRoot;
        currentRoot = newRoot;
        historicalRoots[newRoot] = true;

        emit RootUpdated(oldRoot, newRoot, block.timestamp);
    }

    /**
     * @notice Verifies an inclusion proof against the current SMT root using Poseidon hashing.
     * @dev Implements the @iden3/js-merkletree proof verification logic.
     * @param key The user's address or identifier as a 32-byte key.
     * @param value The user's TrustScore as a 32-byte value.
     * @param siblings The sibling nodes for the Merkle proof.
     * @return bool True if the proof is valid, false otherwise.
     */
    function verifyTrustScore(
        bytes32 key,
        bytes32 value,
        bytes32[] calldata siblings
    ) external view returns (bool) {
        // According to iden3 SMT logic:
        // Hash the leaf node: Hash(key, value, 1)
        // Then hash up the tree: Hash(leftChild, rightChild)

        // Leaf hash using Poseidon(key, value, 1) or Poseidon(key, value)
        // Usually, in iden3 it's Poseidon2(key, value) for leaf if leaf type isn't hashed,
        // actually iden3 js-merkletree leaf hash is Hash(key, value, 1) using Poseidon3
        // Let's implement the standard Poseidon leaf hash for js-merkletree: Hash(key, value, 1)
        uint256 nextHash = hashLeafNode(uint256(key), uint256(value));

        uint256 index = uint256(key);

        for (uint256 i = 0; i < siblings.length; i++) {
            if (siblings[i] != bytes32(0) || nextHash != 0) {
                if ((index >> i) & 1 == 1) {
                    nextHash = hashMiddleNode(uint256(siblings[i]), nextHash);
                } else {
                    nextHash = hashMiddleNode(nextHash, uint256(siblings[i]));
                }
            }
        }

        return bytes32(nextHash) == currentRoot;
    }

    /**
     * @notice Hashes a leaf node using iden3 Poseidon hash.
     * JS Merkletree hashes leaves as Poseidon(key, value, 1)
     */
    function hashLeafNode(uint256 key, uint256 value) internal pure returns (uint256) {
        uint256[3] memory input = [key, value, 1];
        return PoseidonUnit3L.poseidon(input);
    }

    /**
     * @notice Hashes a middle node using iden3 Poseidon hash.
     * JS Merkletree hashes middle nodes as Poseidon(left, right)
     */
    function hashMiddleNode(uint256 left, uint256 right) internal pure returns (uint256) {
        uint256[2] memory input = [left, right];
        return PoseidonUnit2L.poseidon(input);
    }
}
