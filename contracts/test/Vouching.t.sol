// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Vouching} from "../src/Vouching.sol";
import {ERC20} from "openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "openzeppelin-contracts/contracts/access/Ownable.sol";

// A simple mock token for testing
contract MockCRE is ERC20 {
    constructor() ERC20("Mock CRE", "MCRE") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract VouchingTest is Test {
    Vouching public vouching;
    MockCRE public mockToken;

    address public initialOwner = address(0x99);
    address public treasury = address(0x88);

    address public alice = address(0x1);
    address public bob = address(0x2);

    function setUp() public {
        mockToken = new MockCRE();
        vouching = new Vouching(address(mockToken), initialOwner, treasury);

        // Fund test users
        mockToken.mint(alice, 10000 ether);
        mockToken.mint(bob, 10000 ether);

        // Approve the vouching contract
        vm.prank(alice);
        mockToken.approve(address(vouching), type(uint256).max);

        vm.prank(bob);
        mockToken.approve(address(vouching), type(uint256).max);
    }

    /// @notice Test placing a bond successfully
    function test_PlaceBond() public {
        uint256 bondAmount = 100 ether;

        vm.prank(alice);
        vouching.placeBond(bob, bondAmount);

        (uint256 amount, uint256 lockedUntil, bool isActive) = vouching.bonds(alice, bob);

        assertEq(amount, bondAmount);
        assertEq(lockedUntil, block.timestamp + vouching.PROBATION_PERIOD());
        assertTrue(isActive);
        assertEq(mockToken.balanceOf(address(vouching)), bondAmount);
    }

    /// @notice Test trying to withdraw early (before 180 days)
    function test_CannotWithdrawEarly() public {
        uint256 bondAmount = 100 ether;

        vm.prank(alice);
        vouching.placeBond(bob, bondAmount);

        // Fast forward 179 days
        vm.warp(block.timestamp + 179 days);

        vm.prank(alice);
        vm.expectRevert(Vouching.BondStillLocked.selector);
        vouching.withdrawBond(bob);
    }

    /// @notice Test successful withdrawal after 180 days
    function test_WithdrawBondAfterProbation() public {
        uint256 bondAmount = 100 ether;
        uint256 initialAliceBalance = mockToken.balanceOf(alice);

        vm.prank(alice);
        vouching.placeBond(bob, bondAmount);

        // Fast forward exactly 180 days
        vm.warp(block.timestamp + 180 days);

        vm.prank(alice);
        vouching.withdrawBond(bob);

        (uint256 amount, uint256 lockedUntil, bool isActive) = vouching.bonds(alice, bob);

        assertEq(amount, 0);
        assertEq(lockedUntil, 0); // Check delete worked
        assertFalse(isActive);
        assertEq(mockToken.balanceOf(alice), initialAliceBalance); // fully refunded
    }

    /// @notice Test owner can slash a bond successfully
    function test_SlashBond() public {
        uint256 bondAmount = 100 ether;

        vm.prank(alice);
        vouching.placeBond(bob, bondAmount);

        uint256 initialTreasuryBalance = mockToken.balanceOf(treasury);

        vm.prank(initialOwner);
        vouching.slashBond(alice, bob);

        (uint256 amount, uint256 lockedUntil, bool isActive) = vouching.bonds(alice, bob);

        assertEq(amount, 0);
        assertEq(lockedUntil, 0);
        assertFalse(isActive);

        assertEq(mockToken.balanceOf(treasury), initialTreasuryBalance + bondAmount);
    }

    /// @notice Test non-owner cannot slash a bond
    function test_RevertIf_NonOwnerSlashes() public {
        uint256 bondAmount = 100 ether;

        vm.prank(alice);
        vouching.placeBond(bob, bondAmount);

        vm.prank(bob);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, bob));
        vouching.slashBond(alice, bob);
    }

    /// @notice Test updating the treasury
    function test_SetTreasury() public {
        address newTreasury = address(0x77);

        vm.prank(initialOwner);
        vouching.setTreasury(newTreasury);

        assertEq(vouching.treasury(), newTreasury);
    }

    /// @notice Fuzz testing the bond amount
    function testFuzz_PlaceBond(uint256 amount) public {
        // Bound amount between 1 wei and 10000 ether to avoid out of bounds on the mock token
        amount = bound(amount, 1, 10000 ether);

        vm.prank(alice);
        vouching.placeBond(bob, amount);

        (uint256 actualAmount, , bool isActive) = vouching.bonds(alice, bob);
        assertEq(actualAmount, amount);
        assertTrue(isActive);
    }

    /// @notice Fuzz testing trying to break the time lock
    function testFuzz_TimeLockWithdrawal(uint256 timeJump) public {
        uint256 bondAmount = 100 ether;

        vm.prank(alice);
        vouching.placeBond(bob, bondAmount);

        // Ensure timeJump is less than 180 days
        timeJump = bound(timeJump, 0, 180 days - 1);
        vm.warp(block.timestamp + timeJump);

        vm.prank(alice);
        vm.expectRevert(Vouching.BondStillLocked.selector);
        vouching.withdrawBond(bob);
    }

    /// @notice Test Sybil swarm with multiple vouchers bonding one target
    function test_SybilSwarmVouching() public {
        uint256 swarmSize = 50;
        uint256 bondAmount = 10 ether;

        for (uint160 i = 1; i <= swarmSize; i++) {
            address sybilNode = address(i + 100);

            // Setup Sybil
            mockToken.mint(sybilNode, bondAmount);
            vm.startPrank(sybilNode);
            mockToken.approve(address(vouching), bondAmount);

            // Vouch for Bob
            vouching.placeBond(bob, bondAmount);
            vm.stopPrank();
        }

        assertEq(mockToken.balanceOf(address(vouching)), swarmSize * bondAmount);
    }
}
