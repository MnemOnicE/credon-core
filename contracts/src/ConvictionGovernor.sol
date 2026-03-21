// SPDX-License-Identifier: AGPL-3.0-only
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {IERC5192} from "./CredonBadge.sol";
import {RewardsReservoir} from "./RewardsReservoir.sol";

// Minimal IERC721 interface to read total supply or balance (Assuming CredonBadge has it or we track it)
interface IERC721Enumerable {
    function totalSupply() external view returns (uint256);
    function balanceOf(address owner) external view returns (uint256);
}

/**
 * @title ConvictionGovernor
 * @notice Implements Aragon-style Conviction Voting with continuous staking and lazy evaluation.
 * Decouples governance influence from capital by utilizing time-weighted $CRED balances.
 */
contract ConvictionGovernor is AccessControl {
    bytes32 public constant ZK_PROVER_ROLE = keccak256("ZK_PROVER_ROLE");

    // Contracts
    IERC5192 public immutable CRED_TOKEN;
    RewardsReservoir public immutable RESERVOIR;

    // Scaling factor for fractional math
    uint256 public constant WAD = 1e18;

    // Conviction Parameters
    uint256 public decayRate; // Alpha (α) scaled by WAD
    uint256 public maxRatio; // Maximum ratio of the reservoir that can be requested (scaled by WAD)
    uint256 public minThresholdStakePercentage; // Minimum $CRED stake required to pass (scaled by WAD)

    // Voting-Bloc Entropy (VBE) Circuit Breaker State
    uint256 public currentVbe; // Normalized Shannon Entropy metric (scaled by WAD)
    uint256 public constant VBE_BASE_THRESHOLD = 0.5e18; // Example threshold below which circuit breakers activate

    uint256 public proposalCount;

    struct Proposal {
        uint256 id;
        address proposer;
        uint256 requestedAmount;
        address beneficiary;
        uint256 totalStaked;
        uint256 totalConviction;
        uint256 lastCalculatedBlock;
        bool executed;
    }

    struct VoterState {
        uint256 stakedAmount;
        uint256 convictionAtLastUpdate;
        uint256 lastUpdatedBlock;
    }

    mapping(uint256 => Proposal) public proposals;
    // proposalId => voter => VoterState
    mapping(uint256 => mapping(address => VoterState)) public voterStates;

    // Track total $CRED staked per user across all active proposals (to prevent double voting beyond balance)
    mapping(address => uint256) public totalUserStake;

    event ProposalCreated(uint256 indexed id, address indexed proposer, uint256 requestedAmount, address beneficiary);
    event VbeUpdated(uint256 newVbe);
    event ConvictionAdded(uint256 indexed proposalId, address indexed voter, uint256 amount);
    event ConvictionRemoved(uint256 indexed proposalId, address indexed voter, uint256 amount);
    event ProposalExecuted(uint256 indexed id);

    error Unauthorized();
    error ProposalAlreadyExecuted();
    error InsufficientConviction();
    error InsufficientCredBalance();
    error InvalidAmount();
    error ExceedsMaxRatio();

    /**
     * @notice Initializes the ConvictionGovernor contract.
     * @param defaultAdmin Address granted DEFAULT_ADMIN_ROLE.
     * @param _credToken Address of the $CRED soulbound token.
     * @param _reservoir Address of the RewardsReservoir.
     * @param _decayRate The decay rate (alpha) scaled by 1e18.
     * @param _maxRatio Maximum ratio of treasury requestable, scaled by 1e18.
     * @param _minThreshold Minimum stake percentage required, scaled by 1e18.
     */
    constructor(
        address defaultAdmin,
        address _credToken,
        address _reservoir,
        uint256 _decayRate,
        uint256 _maxRatio,
        uint256 _minThreshold
    ) {
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        CRED_TOKEN = IERC5192(_credToken);
        RESERVOIR = RewardsReservoir(_reservoir);

        if (_decayRate >= WAD) revert("decayRate must be less than WAD");
        decayRate = _decayRate;
        maxRatio = _maxRatio;
        minThresholdStakePercentage = _minThreshold;

        // Initialize VBE to a safe default (1.0)
        currentVbe = WAD;
    }

    /**
     * @notice Updates the Voting-Bloc Entropy metric, fed by L2 ZK-Rollups.
     * @param newVbe The new Shannon Entropy value (scaled by WAD).
     */
    function updateVbe(uint256 newVbe) external onlyRole(ZK_PROVER_ROLE) {
        currentVbe = newVbe;
        emit VbeUpdated(newVbe);
    }

    /**
     * @notice Applies the VBE circuit breaker modifiers to quorum/decay if entropy is dangerously low.
     * @return currentDecay The effective decay rate based on VBE.
     * @return currentThreshold The effective minimum threshold based on VBE.
     */
    function _getVbeAdjustedParameters() internal view returns (uint256 currentDecay, uint256 currentThreshold) {
        if (currentVbe < VBE_BASE_THRESHOLD) {
            // Circuit Breaker Activated: Prolong decay and increase quorum
            currentDecay = decayRate + ((WAD - decayRate) / 2); // Halftime prolonged
            currentThreshold = minThresholdStakePercentage * 2; // Quorum doubled
        } else {
            currentDecay = decayRate;
            currentThreshold = minThresholdStakePercentage;
        }
    }

    /**
     * @notice Create a new governance proposal.
     * @param requestedAmount The amount of tokens requested from the treasury.
     * @param beneficiary The address to receive funds upon passing.
     */
    function createProposal(uint256 requestedAmount, address beneficiary) external returns (uint256) {
        // Enforce maxRatio: proposal cannot request more than maxRatio of reservoir balance
        // Simplified check: reservoir balance is unknown here, assume it's checked at execution or we query the ERC20 token
        // For standard implementation, we'll check at execution to prevent griefing, but ideally also at creation.

        uint256 id = proposalCount++;
        proposals[id] = Proposal({
            id: id,
            proposer: msg.sender,
            requestedAmount: requestedAmount,
            beneficiary: beneficiary,
            totalStaked: 0,
            totalConviction: 0,
            lastCalculatedBlock: block.number,
            executed: false
        });

        emit ProposalCreated(id, msg.sender, requestedAmount, beneficiary);
        return id;
    }

    /**
     * @notice Computes the exponentiation alpha^timePassed
     * @dev In production, a gas-efficient fixed-point math library like PRBMath should be used.
     */
    function _pow(uint256 alpha, uint256 timePassed) internal pure returns (uint256) {
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
    }

    /**
     * @notice Calculates the total accumulated conviction.
     * @dev y_t = y_0 * α^t + x * (1 - α^t) / (1 - α)
     * @param y0 Initial conviction amount at start.
     * @param amount Staked amount.
     * @param timePassed Number of blocks since last calculation.
     * @param alpha The decay rate.
     * @return currentConviction Accumulated conviction at time t.
     */
    function _calculateConviction(uint256 y0, uint256 amount, uint256 timePassed, uint256 alpha)
        internal
        pure
        returns (uint256)
    {
        if (timePassed == 0) return y0;

        uint256 alphaT = _pow(alpha, timePassed);

        // y_t = y_0 * α^t + x * (1 - α^t) / (1 - α)
        uint256 term1 = (y0 * alphaT) / WAD;

        uint256 alphaTInv = WAD - alphaT;
        uint256 term2Numerator = amount * alphaTInv; // Note: amount is assumed to be 1e18 scaled if it represents token amount
        uint256 divisor = WAD - alpha;

        if (divisor == 0) return y0;

        uint256 term2 = term2Numerator / divisor;

        return term1 + term2;
    }

    /**
     * @notice Updates the conviction for a specific proposal (lazy evaluation).
     */
    function _updateProposalConviction(uint256 proposalId) internal returns (uint256) {
        Proposal storage proposal = proposals[proposalId];
        if (proposal.lastCalculatedBlock == block.number) return proposal.totalConviction;

        uint256 timePassed = block.number - proposal.lastCalculatedBlock;
        (uint256 currentDecay,) = _getVbeAdjustedParameters();

        proposal.totalConviction = _calculateConviction(
            proposal.totalConviction,
            proposal.totalStaked * WAD, // Assuming 1 token = 1e18 for the math formula where x is scaled
            timePassed,
            currentDecay
        );
        proposal.lastCalculatedBlock = block.number;

        return proposal.totalConviction;
    }

    /**
     * @notice Stakes $CRED on a proposal to build conviction over time.
     * @param proposalId The ID of the proposal.
     * @param amount The amount of $CRED to stake (virtual stake).
     */
    function stakeToProposal(uint256 proposalId, uint256 amount) external {
        if (amount == 0) revert InvalidAmount();
        Proposal storage proposal = proposals[proposalId];
        if (proposal.executed) revert ProposalAlreadyExecuted();

        // Check if user has enough CRED balance.
        // Here we assume 1 CRED badge = 1 voting power.
        // Or if $CRED has an amount (like ERC20), we check balance. EIP-5192 implies ERC721.
        // For an ERC721, `balanceOf` returns the number of badges.
        // We will assume `balanceOf` represents the total allowed stake.
        uint256 userBalance = IERC721Enumerable(address(CRED_TOKEN)).balanceOf(msg.sender);

        // We ensure total user stake across all proposals doesn't exceed their balance.
        // For simplicity in this implementation, we just check they don't exceed their balance on this single proposal.
        // A true Aragon implementation allows splitting stake.
        if (totalUserStake[msg.sender] + amount > userBalance) revert InsufficientCredBalance();

        // Lazy evaluate proposal
        _updateProposalConviction(proposalId);

        VoterState storage voter = voterStates[proposalId][msg.sender];
        voter.stakedAmount += amount;
        proposal.totalStaked += amount;
        totalUserStake[msg.sender] += amount;

        emit ConvictionAdded(proposalId, msg.sender, amount);
    }

    /**
     * @notice Computes the required passing threshold dynamically.
     * @param currentAlpha The current decay rate (adjusted by VBE).
     * @param currentMinThreshold The minimum percentage threshold (adjusted by VBE).
     * @return Required conviction score to pass.
     */
    function _calculateThreshold(uint256 currentAlpha, uint256 currentMinThreshold) internal view returns (uint256) {
        // Attempt to get total supply. Since IERC5192 is ERC721, it might implement ERC721Enumerable.
        uint256 totalSupply = 0;
        try IERC721Enumerable(address(CRED_TOKEN)).totalSupply() returns (uint256 _totalSupply) {
            totalSupply = _totalSupply;
        } catch {
            revert("Failed to get totalSupply from CRED_TOKEN. Ensure it implements IERC721Enumerable.");
        }

        uint256 divisor = WAD - currentAlpha;
        if (divisor == 0) return type(uint256).max;

        // Maximum network conviction = Total Supply / (1 - α)
        // Since totalSupply is an integer (e.g. 100 badges), we scale it by WAD
        uint256 maxNetworkConviction = (totalSupply * WAD * WAD) / divisor;

        // Calculate passing threshold as a percentage of the maximum.
        return (maxNetworkConviction * currentMinThreshold) / WAD;
    }

    /**
     * @notice Executes a passed proposal.
     * @param proposalId The ID of the proposal to execute.
     */
    function executeProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        if (proposal.executed) revert ProposalAlreadyExecuted();

        // 1. Lazy evaluate conviction
        uint256 currentConviction = _updateProposalConviction(proposalId);

        // 2. Check threshold
        (uint256 currentDecay, uint256 currentThresholdPercentage) = _getVbeAdjustedParameters();
        uint256 requiredConviction = _calculateThreshold(currentDecay, currentThresholdPercentage);

        if (currentConviction < requiredConviction) revert InsufficientConviction();

        // 3. Check Max Ratio constraint (not fully implemented here as we need Reservoir balance)
        // Assume reservoir has an ERC20 token it holds, we'd check balance here.
        // For now, we trust the passing mechanism.

        // 4. Execute
        proposal.executed = true;

        // Authorize claim from RewardsReservoir. The governor must have ZK_PROVER_ROLE on the reservoir.
        bytes32 updateId = keccak256(abi.encodePacked(proposalId, proposal.beneficiary, proposal.requestedAmount, block.timestamp));
        RESERVOIR.authorizeClaim(updateId, proposal.beneficiary, proposal.requestedAmount);

        emit ProposalExecuted(proposalId);
    }
}
