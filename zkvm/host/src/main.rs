use methods::{METHOD_ELF, METHOD_ID};
use risc0_zkvm::{default_prover, ExecutorEnv};
use serde::{Deserialize, Serialize};
const SCALE: i64 = 10_000;
const MAX_NODES: usize = 8;
#[derive(Serialize, Deserialize)]
pub struct TrustInput {
    pub interactions: Vec<Vec<i64>>,
}
#[derive(Serialize, Deserialize, Debug)]
pub struct TrustOutput {
    pub transitive_trust: Vec<i64>,
    pub social_connectivity: Vec<i64>,
}
fn main() {
    println!("Initializing TrustLedger Guest Prover (Fixed-Point, Stack Arrays)...");
    let n = 8;
    let mut interactions = [[0; MAX_NODES]; MAX_NODES];
    let weight = 400 * SCALE;
    let sybil_weight = 2000 * SCALE;
    interactions[0][1] = weight;
    interactions[1][2] = weight;
    interactions[2][3] = weight;
    interactions[3][4] = weight;
    interactions[4][0] = weight;
    interactions[0][2] = weight;
    interactions[0][5] = weight;
    interactions[5][6] = sybil_weight;
    interactions[6][7] = sybil_weight;
    interactions[7][5] = sybil_weight;
    interactions[5][7] = sybil_weight;
    let mut interactions_vec = vec![vec![0; n]; n];
    for i in 0..n {
        for j in 0..n {
            interactions_vec[i][j] = interactions[i][j];
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
    println!("Generating ZK Proof for EigenTrust & PageRank (Native Arrays, i64, Scale 1e4)...");
    let receipt = prover.prove(env, METHOD_ELF).unwrap().receipt;
    println!("ZK Proof successfully generated!");
    let output: TrustOutput = receipt.journal.decode().unwrap();
    println!("\n--- Results ---");
    println!("Transitive Trust (EigenTrust):");
    for (i, val) in output.transitive_trust.iter().enumerate() {
        println!("  Agent {}: {:.4}", i, *val as f64 / SCALE as f64);
    }
    println!("\nSocial Connectivity (PageRank):");
    for (i, val) in output.social_connectivity.iter().enumerate() {
        println!("  Agent {}: {:.4}", i, *val as f64 / SCALE as f64);
    }
    receipt.verify(METHOD_ID).unwrap();
    println!("\nReceipt verified successfully!");
}
