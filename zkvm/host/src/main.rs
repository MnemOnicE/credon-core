use nalgebra::DMatrix;
use methods::{METHOD_ELF, METHOD_ID};
use risc0_zkvm::{default_prover, ExecutorEnv};
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct TrustInput {
    pub interactions: Vec<Vec<f64>>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct TrustOutput {
    pub transitive_trust: Vec<f64>,
    pub social_connectivity: Vec<f64>,
}

fn main() {
    println!("Initializing TrustLedger Guest Prover...");

    // Create a mock adjacency matrix with 5 honest nodes and a 3-node Sybil Link Farm
    // 0-4: Honest Agents
    // 5-7: Sybil Attackers (Link Farm)
    let n = 8;
    let mut interactions = DMatrix::zeros(n, n);

    // Honest nodes interact with each other loosely
    interactions[(0, 1)] = 400.0;
    interactions[(1, 2)] = 400.0;
    interactions[(2, 3)] = 400.0;
    interactions[(3, 4)] = 400.0;
    interactions[(4, 0)] = 400.0;
    interactions[(0, 2)] = 400.0;

    // Honest node 0 accidentally interacts with Sybil 5
    interactions[(0, 5)] = 400.0;

    // Sybils tightly link farm with each other with high weights
    interactions[(5, 6)] = 2000.0;
    interactions[(6, 7)] = 2000.0;
    interactions[(7, 5)] = 2000.0;
    interactions[(5, 7)] = 2000.0;

    let mut interactions_vec = vec![vec![0.0; n]; n];
    for i in 0..n {
        for j in 0..n {
            interactions_vec[i][j] = interactions[(i, j)];
        }
    }

    let input = TrustInput {
        interactions: interactions_vec,
    };

    let env = ExecutorEnv::builder()
        .write(&input)
        .unwrap()
        .build()
        .unwrap();

    let prover = default_prover();

    println!("Generating ZK Proof for EigenTrust & PageRank...");
    let receipt = prover
        .prove(env, METHOD_ELF)
        .unwrap()
        .receipt;

    println!("ZK Proof successfully generated!");

    let output: TrustOutput = receipt.journal.decode().unwrap();

    println!("\n--- Results ---");
    println!("Transitive Trust (EigenTrust):");
    for (i, val) in output.transitive_trust.iter().enumerate() {
        println!("  Agent {}: {:.4}", i, val);
    }

    println!("\nSocial Connectivity (PageRank):");
    for (i, val) in output.social_connectivity.iter().enumerate() {
        println!("  Agent {}: {:.4}", i, val);
    }

    // Verify receipt (optional but good practice)
    receipt.verify(METHOD_ID).unwrap();
    println!("\nReceipt verified successfully!");
}
