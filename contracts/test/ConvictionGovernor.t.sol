// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ConvictionGovernor} from "../src/ConvictionGovernor.sol";
import {CredonBadge} from "../src/CredonBadge.sol";
import {RewardsReservoir} from "../src/RewardsReservoir.sol";
import {CredonToken} from "../src/CredonToken.sol";

contract ConvictionGovernorTest is Test {
    ConvictionGovernor public governor;
    CredonBadge public credToken;
    RewardsReservoir public reservoir;
    CredonToken public rewardToken;

    address public admin = address(1);
    address public zkProver = address(2);
    address public minter = address(3);
    address public voter1 = address(4);
    address public voter2 = address(5);
    address public beneficiary = address(6);

    uint256 public constant WAD = 1e18;
    uint256 public constant DECAY_RATE = 0.99e18; // 99% decay rate (alpha)
    uint256 public constant MAX_RATIO = 0.2e18; // 20% max requested
    uint256 public constant MIN_THRESHOLD = 0.2e18; // 20% passing threshold

    function setUp() public {
        vm.startPrank(admin);

        // Setup $CRE token (dummy logic)
        rewardToken = new CredonToken(admin);

        // Setup $CRED
        credToken = new CredonBadge(admin);
        credToken.grantRole(credToken.MINTER_ROLE(), minter);

        // Setup Reservoir
        reservoir = new RewardsReservoir(admin, address(rewardToken), 1000 * WAD);

        // Setup Governor
        governor =
            new ConvictionGovernor(admin, address(credToken), address(reservoir), DECAY_RATE, MAX_RATIO, MIN_THRESHOLD);

        governor.grantRole(governor.ZK_PROVER_ROLE(), zkProver);

        vm.stopPrank();

        // Mint badges for voters
        vm.startPrank(minter);
        credToken.mint(voter1, 1);
        credToken.mint(voter2, 2);
        vm.stopPrank();
    }

    function test_Initialization() public view {
        assertEq(governor.decayRate(), DECAY_RATE);
        assertEq(governor.maxRatio(), MAX_RATIO);
        assertEq(governor.minThresholdStakePercentage(), MIN_THRESHOLD);
        assertEq(governor.currentVbe(), WAD);
        assertTrue(governor.hasRole(governor.ZK_PROVER_ROLE(), zkProver));
        assertEq(address(governor.CRED_TOKEN()), address(credToken));
        assertEq(address(governor.RESERVOIR()), address(reservoir));
    }

    function test_CreateProposal() public {
        vm.prank(voter1);
        uint256 proposalId = governor.createProposal(100 * WAD, beneficiary);

        assertEq(proposalId, 0);

        (
            uint256 id,
            address proposer,
            uint256 requestedAmount,
            address ben,
            uint256 totalStaked,
            uint256 totalConviction,
            uint256 lastCalculatedBlock,
            bool executed
        ) = governor.proposals(proposalId);

        assertEq(id, 0);
        assertEq(proposer, voter1);
        assertEq(requestedAmount, 100 * WAD);
        assertEq(ben, beneficiary);
        assertEq(totalStaked, 0);
        assertEq(totalConviction, 0);
        assertEq(lastCalculatedBlock, block.number);
        assertFalse(executed);
    }

    function test_UpdateVbe_ByZkProver() public {
        uint256 newVbe = 0.8e18;

        vm.prank(zkProver);
        governor.updateVbe(newVbe);

        assertEq(governor.currentVbe(), newVbe);
    }

    function test_UpdateVbe_RevertUnauthorized() public {
        uint256 newVbe = 0.8e18;

        vm.prank(voter1);
        vm.expectRevert();
        governor.updateVbe(newVbe);
    }

    function test_StakeToProposal() public {
        vm.startPrank(voter1);
        uint256 proposalId = governor.createProposal(100 * WAD, beneficiary);

        governor.stakeToProposal(proposalId, 1); // Staking 1 badge

        (,,,, uint256 totalStaked,,,) = governor.proposals(proposalId);
        assertEq(totalStaked, 1);
        vm.stopPrank();
    }

    function test_StakeToProposal_RevertInsufficientBalance() public {
        vm.startPrank(voter1);
        uint256 proposalId = governor.createProposal(100 * WAD, beneficiary);

        // Voter1 only has 1 badge, trying to stake 2
        vm.expectRevert(ConvictionGovernor.InsufficientCredBalance.selector);
        governor.stakeToProposal(proposalId, 2);
        vm.stopPrank();
    }
}
