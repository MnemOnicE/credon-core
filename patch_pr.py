import re

with open('contracts/src/ConvictionGovernor.sol', 'r') as f:
    content = f.read()

# Fix 1: _pow function to use Exponentiation by Squaring
pow_orig = """    function _pow(uint256 alpha, uint256 timePassed) internal pure returns (uint256) {
        uint256 res = WAD;
        for (uint256 i = 0; i < timePassed; i++) {
            res = (res * alpha) / WAD;
        }
        return res;
    }"""
pow_new = """    function _pow(uint256 alpha, uint256 timePassed) internal pure returns (uint256) {
        if (timePassed == 0) {
            return WAD;
        }
        uint256 res = WAD;
        uint256 base = alpha;
        while (timePassed > 0) {
            if (timePassed % 2 == 1) {
                res = (res * base) / WAD;
            }
            base = (base * base) / WAD;
            timePassed /= 2;
        }
        return res;
    }"""
content = content.replace(pow_orig, pow_new)

# Fix 2: Staking logic flaw (totalUserStake)
stake_orig = """        VoterState storage voter = voterStates[proposalId][msg.sender];
        if (voter.stakedAmount + amount > userBalance) revert InsufficientCredBalance();

        // Lazy evaluate proposal
        _updateProposalConviction(proposalId);

        voter.stakedAmount += amount;
        proposal.totalStaked += amount;"""
stake_new = """        if (totalUserStake[msg.sender] + amount > userBalance) revert InsufficientCredBalance();

        // Lazy evaluate proposal
        _updateProposalConviction(proposalId);

        VoterState storage voter = voterStates[proposalId][msg.sender];
        voter.stakedAmount += amount;
        proposal.totalStaked += amount;
        totalUserStake[msg.sender] += amount;"""
content = content.replace(stake_orig, stake_new)

# Fix 3: executeProposal interaction with RewardsReservoir
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

# Fix 4: Constructor validation for decayRate
init_orig = """        decayRate = _decayRate;
        maxRatio = _maxRatio;
        minThresholdStakePercentage = _minThreshold;"""
init_new = """        if (_decayRate >= WAD) revert("decayRate must be less than WAD");
        decayRate = _decayRate;
        maxRatio = _maxRatio;
        minThresholdStakePercentage = _minThreshold;"""
content = content.replace(init_orig, init_new)

with open('contracts/src/ConvictionGovernor.sol', 'w') as f:
    f.write(content)
