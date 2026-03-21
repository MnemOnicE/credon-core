// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {console2} from "forge-std/console2.sol";
import {CredonToken} from "../src/CredonToken.sol";
import {CredonBadge} from "../src/CredonBadge.sol";
import {RewardsReservoir} from "../src/RewardsReservoir.sol";
import {ConvictionGovernor} from "../src/ConvictionGovernor.sol";

contract DeployScript is Script {
    function run() public {
        // Read deploy_config.json from project root
        string memory root = vm.projectRoot();
        // project root for contracts is /app/contracts. We wrote deploy_config.json to /app.
        string memory path = string.concat(root, "/deploy_config.json");
        string memory json = vm.readFile(path);

        // Parse optimal parameters
        uint256 decayRate = vm.parseJsonUint(json, ".decayRate");
        uint256 maxRatio = vm.parseJsonUint(json, ".maxRatio");
        uint256 minThreshold = vm.parseJsonUint(json, ".minThresholdStakePercentage");
        uint256 initialMaxTokensPerEpoch = vm.parseJsonUint(json, ".initialMaxTokensPerEpoch");

        console2.log("Loaded configurations from Python simulation:");
        console2.log("Decay Rate:", decayRate);
        console2.log("Max Ratio:", maxRatio);
        console2.log("Min Threshold:", minThreshold);
        console2.log("Initial Epoch Emission Limit:", initialMaxTokensPerEpoch);

        // Setup deployer key
        uint256 deployerPrivateKey = vm.envOr("PRIVATE_KEY", uint256(1));
        address defaultAdmin = vm.addr(deployerPrivateKey);

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy Tokens
        CredonToken credToken = new CredonToken(defaultAdmin);
        console2.log("Deployed CredonToken at:", address(credToken));

        CredonBadge credBadge = new CredonBadge(defaultAdmin);
        console2.log("Deployed CredonBadge at:", address(credBadge));

        // 2. Deploy Reservoir
        RewardsReservoir reservoir = new RewardsReservoir(
            defaultAdmin,
            address(credToken),
            initialMaxTokensPerEpoch
        );
        console2.log("Deployed RewardsReservoir at:", address(reservoir));

        // 3. Deploy Governor
        ConvictionGovernor governor = new ConvictionGovernor(
            defaultAdmin,
            address(credBadge),
            address(reservoir),
            decayRate,
            maxRatio,
            minThreshold
        );
        console2.log("Deployed ConvictionGovernor at:", address(governor));

        // 4. Setup Roles (Assuming defaultAdmin configures them)
        // Governor must have ZK_PROVER_ROLE on Reservoir
        reservoir.grantRole(reservoir.ZK_PROVER_ROLE(), address(governor));

        // Reservoir must have MINTER_ROLE on CredonToken
        credToken.grantRole(credToken.MINTER_ROLE(), address(reservoir));

        // We'll leave ZK_PROVER_ROLE on Governor to be assigned later by admin
        // We also leave MINTER_ROLE on CredonBadge to be assigned later

        vm.stopBroadcast();

        console2.log("Deployment complete.");
    }
}
