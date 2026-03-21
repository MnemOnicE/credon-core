import re

with open('contracts/src/ConvictionGovernor.sol', 'r') as f:
    content = f.read()

execute_orig = """        // Note: The reservoir would need a function to process this claim.
        // We will call a generic `executeReward` function on the reservoir.
        // Since RewardsReservoir signature is not fully known, we stub the call or use a low-level call.

        // (bool success, ) = address(RESERVOIR).call(
        //     abi.encodeWithSignature("claimRewards(address,uint256)", proposal.beneficiary, proposal.requestedAmount)
        // );
        // require(success, "Execution failed");"""
execute_new = """        // Authorize claim from RewardsReservoir. The governor must have ZK_PROVER_ROLE on the reservoir.
        bytes32 updateId = keccak256(abi.encodePacked(proposalId, proposal.beneficiary, proposal.requestedAmount, block.timestamp));
        RESERVOIR.authorizeClaim(updateId, proposal.beneficiary, proposal.requestedAmount);"""
content = content.replace(execute_orig, execute_new)

with open('contracts/src/ConvictionGovernor.sol', 'w') as f:
    f.write(content)
