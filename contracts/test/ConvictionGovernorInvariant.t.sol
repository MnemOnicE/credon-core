// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity >=0.8.24;

import {Test} from "forge-std/Test.sol";
import {ConvictionGovernor} from "../src/ConvictionGovernor.sol";
import {CredonToken} from "../src/CredonToken.sol";
import {CredonBadge} from "../src/CredonBadge.sol";
import {RewardsReservoir} from "../src/RewardsReservoir.sol";

// Expose internal calculate function to test conviction bounds
contract TestableConvictionGovernor is ConvictionGovernor {
    constructor(
        address defaultAdmin,
        address _credToken,
        address _reservoir,
        uint256 _decayRate,
        uint256 _maxRatio,
        uint256 _minThreshold
    ) ConvictionGovernor(defaultAdmin, _credToken, _reservoir, _decayRate, _maxRatio, _minThreshold) {}

    function calculateConvictionPublic(uint256 y0, uint256 amount, uint256 timePassed, uint256 alpha)
        public
        pure
        returns (uint256)
    {
        return _calculateConviction(y0, amount, timePassed, alpha);
    }
}

contract ConvictionGovernorInvariantTest is Test {
    TestableConvictionGovernor public governor;
    CredonToken public credToken;
    CredonBadge public credBadge;
    RewardsReservoir public reservoir;

    address public admin = address(this);

    uint256 public constant WAD = 1e18;

    function setUp() public {
        credToken = new CredonToken(admin);
        credBadge = new CredonBadge(admin);
        reservoir = new RewardsReservoir(admin, address(credToken), 1000 * WAD);

        governor = new TestableConvictionGovernor(
            admin,
            address(credBadge),
            address(reservoir),
            0.9e18, // decayRate: 0.9
            0.2e18,  // maxRatio: 20%
            0.1e18   // minThreshold: 10%
        );
    }

    function testFuzz_ConvictionNeverExceedsMax(uint256 y0, uint256 amount, uint256 timePassed, uint256 alpha) public {
        // Bound alpha between 0.1 and 0.999 (avoid 1.0 which causes div by zero)
        alpha = bound(alpha, 0.1e18, 0.999e18);

        // Time passed (blocks) from 0 to 100,000 blocks
        timePassed = bound(timePassed, 0, 100000);

        // Amount staked (up to 1 million tokens scaled)
        amount = bound(amount, 0, 1000000 * WAD);

        // Max theoretical is amount / (1 - alpha)
        // Note: the formula in ConvictionGovernor is: amount * alphaTInv / divisor
        // Where divisor = WAD - alpha
        uint256 maxTheoretical = 0;
        if (WAD - alpha > 0) {
            maxTheoretical = (amount * WAD) / (WAD - alpha);
        }

        // Start conviction below max
        if (maxTheoretical > 0) {
            y0 = bound(y0, 0, maxTheoretical);
        } else {
            y0 = 0;
        }

        uint256 conviction = governor.calculateConvictionPublic(y0, amount, timePassed, alpha);

        // Allow a microscopic tolerance of dust (10 wei)
        assertLe(conviction, maxTheoretical + 10);
    }
    function testFuzz_ConvictionDecaysToDust(uint256 y0, uint256 timePassed, uint256 alpha) public {
        // Bound alpha. If alpha is extremely close to 1 (like 0.999), decay takes exponentially longer.
        // Let's bound it between 0.1 and 0.9 to simulate realistic network configurations
        // where it doesn't take centuries to decay.
        alpha = bound(alpha, 0.1e18, 0.9e18);

        // Bound y0 up to 1 million scaled conviction
        y0 = bound(y0, 0, 1000000 * WAD);

        // Time passed: we need enough blocks to decay.
        // For alpha=0.9, 0.9^1000 = 1.7e-46, which is basically 0.
        // Let's bound timePassed large enough to ensure decay to zero, e.g., 2000+ blocks.
        timePassed = bound(timePassed, 2000, 100000);

        // Amount staked is 0, so it should decay
        uint256 conviction = governor.calculateConvictionPublic(y0, 0, timePassed, alpha);

        // Assert that the remaining dust is within a microscopic tolerance (<= 10 wei)
        assertLe(conviction, 10, "Conviction did not decay to dust");
    }
}
