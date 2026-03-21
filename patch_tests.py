import re

with open('contracts/test/ConvictionGovernor.t.sol', 'r') as f:
    content = f.read()

content = content.replace(
"""        // Setup Reservoir
        reservoir = new RewardsReservoir(admin, address(rewardToken), 1000 * WAD);
        rewardToken.grantRole(rewardToken.MINTER_ROLE(), address(reservoir)); // Reservoir needs to mint

        // Setup Governor""",
"""        // Setup Reservoir
        reservoir = new RewardsReservoir(admin, address(rewardToken), 1000 * WAD);

        // Grant MINTER_ROLE on reward token to the reservoir so it can mint claims
        rewardToken.grantRole(rewardToken.MINTER_ROLE(), address(reservoir));

        // Setup Governor""")

with open('contracts/test/ConvictionGovernor.t.sol', 'w') as f:
    f.write(content)
