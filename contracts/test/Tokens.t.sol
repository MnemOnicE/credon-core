// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity 0.8.27;

import {Test} from "forge-std/Test.sol";
import {CredonToken} from "../src/CredonToken.sol";
import {CredonBadge} from "../src/CredonBadge.sol";
import {RewardsReservoir} from "../src/RewardsReservoir.sol";

contract TokensTest is Test {
    CredonToken public cre;
    CredonBadge public cred;
    RewardsReservoir public reservoir;

    address public admin = address(0x1);
    address public minter = address(0x2);
    address public zkProver = address(0x3);
    address public alice = address(0x4);
    address public bob = address(0x5);

    uint256 public constant INITIAL_MAX_EMISSION = 1000 * 1e18; // 1000 tokens per epoch

    function setUp() public {
        vm.startPrank(admin);

        cre = new CredonToken(admin);
        cred = new CredonBadge(admin);
        // Set initial emission to 1000 $CRE
        reservoir = new RewardsReservoir(admin, address(cre), INITIAL_MAX_EMISSION);

        // Grant Roles
        cre.grantRole(cre.MINTER_ROLE(), address(reservoir));
        cre.grantRole(cre.MINTER_ROLE(), minter);

        cred.grantRole(cred.MINTER_ROLE(), minter);

        reservoir.grantRole(reservoir.ZK_PROVER_ROLE(), zkProver);

        vm.stopPrank();
    }

    // --- CredonToken ($CRE) Tests ---

    function test_CredonToken_AdminHasRole() public {
        assertTrue(cre.hasRole(cre.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_CredonToken_MintRestricted() public {
        vm.prank(alice);
        vm.expectRevert();
        cre.mint(alice, 100);
    }

    function test_CredonToken_MintAllowed() public {
        vm.prank(minter);
        cre.mint(alice, 100);
        assertEq(cre.balanceOf(alice), 100);
    }

    // --- CredonBadge ($CRED) Tests ---

    function test_CredonBadge_LockedReturnsTrue() public {
        vm.prank(minter);
        cred.mint(alice, 1);

        assertTrue(cred.locked(1));
    }

    function test_CredonBadge_MintRestricted() public {
        vm.prank(alice);
        vm.expectRevert();
        cred.mint(alice, 1);
    }

    function test_CredonBadge_TransferReverts() public {
        vm.prank(minter);
        cred.mint(alice, 1);

        vm.prank(alice);
        vm.expectRevert(CredonBadge.TransferNotAllowed.selector);
        cred.transferFrom(alice, bob, 1);

        vm.prank(alice);
        vm.expectRevert(CredonBadge.TransferNotAllowed.selector);
        cred.safeTransferFrom(alice, bob, 1);
    }

    // --- RewardsReservoir Tests ---

    function test_RewardsReservoir_AuthorizeClaimRestricted() public {
        bytes32 updateId = keccak256("update1");

        vm.prank(alice);
        vm.expectRevert();
        reservoir.authorizeClaim(updateId, alice, 500 * 1e18);
    }

    function test_RewardsReservoir_AuthorizeClaimSuccess() public {
        bytes32 updateId = keccak256("update1");

        vm.prank(zkProver);
        reservoir.authorizeClaim(updateId, alice, 500 * 1e18);

        assertEq(cre.balanceOf(alice), 500 * 1e18);
        assertTrue(reservoir.processedStateUpdates(updateId));
        assertEq(reservoir.tokensMintedThisEpoch(), 500 * 1e18);
    }

    function test_RewardsReservoir_AuthorizeClaimPreventsReplay() public {
        bytes32 updateId = keccak256("update1");

        vm.prank(zkProver);
        reservoir.authorizeClaim(updateId, alice, 500 * 1e18);

        vm.prank(zkProver);
        vm.expectRevert(RewardsReservoir.UpdateAlreadyProcessed.selector);
        reservoir.authorizeClaim(updateId, bob, 500 * 1e18);
    }

    function test_RewardsReservoir_RateLimitReverts() public {
        bytes32 updateId1 = keccak256("update1");
        bytes32 updateId2 = keccak256("update2");

        vm.startPrank(zkProver);

        // Claim exactly up to the limit is fine
        reservoir.authorizeClaim(updateId1, alice, INITIAL_MAX_EMISSION);

        // Next claim should fail because limit is exhausted
        vm.expectRevert(abi.encodeWithSelector(RewardsReservoir.EmissionLimitExceeded.selector, 1, 0));
        reservoir.authorizeClaim(updateId2, bob, 1);

        vm.stopPrank();
    }

    function test_RewardsReservoir_TimeLockResetsLimit() public {
        bytes32 updateId1 = keccak256("update1");
        bytes32 updateId2 = keccak256("update2");

        vm.startPrank(zkProver);

        // Exhaust the limit
        reservoir.authorizeClaim(updateId1, alice, INITIAL_MAX_EMISSION);

        // Fast forward time to the next epoch
        vm.warp(block.timestamp + reservoir.EPOCH_DURATION());

        // Now claim should succeed again
        reservoir.authorizeClaim(updateId2, bob, INITIAL_MAX_EMISSION);

        assertEq(cre.balanceOf(bob), INITIAL_MAX_EMISSION);
        assertEq(reservoir.tokensMintedThisEpoch(), INITIAL_MAX_EMISSION);

        vm.stopPrank();
    }

    function test_RewardsReservoir_AdminCanUpdateEmissionLimit() public {
        uint256 newLimit = 2000 * 1e18;

        vm.prank(admin);
        reservoir.setMaxTokensPerEpoch(newLimit);

        assertEq(reservoir.maxTokensPerEpoch(), newLimit);

        bytes32 updateId = keccak256("update1");
        vm.prank(zkProver);
        // Claim using new limit which is more than INITIAL_MAX_EMISSION
        reservoir.authorizeClaim(updateId, alice, 1500 * 1e18);

        assertEq(cre.balanceOf(alice), 1500 * 1e18);
    }
}
