require('dotenv').config();
const { ethers } = require('ethers');
const { Merkletree, InMemoryDB, str2Bytes, Hash } = require('@iden3/js-merkletree');

// Setup mock TrustScores for agents
const MOCK_SCORES = [
    { address: '0x1234567890123456789012345678901234567890', score: 850n },
    { address: '0x2345678901234567890123456789012345678901', score: 920n },
    { address: '0x3456789012345678901234567890123456789012', score: 710n }
];

async function main() {
    console.log("Initializing iden3 Sparse Merkle Tree (SMT)...");

    // 1. Initialize SMT (in memory for mock)
    const storage = new InMemoryDB(str2Bytes(""));
    // 64 is the max depth we set in the TrustLedgerSmt contract
    const mt = new Merkletree(storage, true, 64);

    let rootHashHex;
    try {
        console.log("Aggregating global TrustScores and building SMT...");

        for (let entry of MOCK_SCORES) {
            let addrInt = BigInt(entry.address);
            await mt.add(addrInt, entry.score);
            console.log(`Added leaf: Key (Address)=${addrInt.toString(16)}, Value (Score)=${entry.score}`);
        }

        let rootHash = await mt.root();
        rootHashHex = "0x" + rootHash.bigInt().toString(16).padStart(64, '0');
        console.log(`Computed new SMT Root Hash: ${rootHashHex}`);

        // Modularized proof generation logic for one of the agents
        let testAgent = MOCK_SCORES[0];
        console.log(`\nGenerating inclusion proof for agent ${testAgent.address}...`);

        let { proof, value } = await mt.generateProof(BigInt(testAgent.address), rootHash);

        console.log(`Proof generated!`);
        console.log(`Existence: ${proof.existence}`);
        console.log(`Siblings: ${proof.siblings.length} nodes`);

        // This proof can be swapped with dummy proofs for L1 verification testing if local CPU constraints are hit later
        let siblingStrings = proof.siblings.map(s => "0x" + s.bigInt().toString(16).padStart(64, '0'));
        // console.log("Siblings array (hex):", siblingStrings);

    } catch(err) {
        console.error("Error computing SMT:", err);
        return;
    }

    // 2. Submit to Anvil
    const rpcUrl = process.env.RPC_URL || 'http://127.0.0.1:8545';
    const privateKey = process.env.PRIVATE_KEY;
    if (!privateKey) {
        console.error('No PRIVATE_KEY provided. Please set the PRIVATE_KEY environment variable.');
        process.exit(1);
    }
    const contractAddress = process.env.CONTRACT_ADDRESS; // Address of TrustLedgerSmt

    if (!contractAddress) {
        console.log("\nNo CONTRACT_ADDRESS provided. Skipping L1 submission. Run this script with CONTRACT_ADDRESS set after deploying via Foundry.");
        return;
    }

    console.log(`\nConnecting to local Anvil node at ${rpcUrl}`);
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const wallet = new ethers.Wallet(privateKey, provider);

    // Minimal ABI for TrustLedgerSmt
    const abi = [
        "function updateRoot(bytes32 newRoot) external"
    ];

    const contract = new ethers.Contract(contractAddress, abi, wallet);

    console.log(`Submitting new root to L1 contract...`);
    try {
        const tx = await contract.updateRoot(rootHashHex);
        console.log(`Transaction submitted! Hash: ${tx.hash}`);
        await tx.wait();
        console.log("Transaction mined successfully.");
    } catch (err) {
        console.error("Failed to submit transaction:", err.message);
    }
}

main().catch(console.error);
