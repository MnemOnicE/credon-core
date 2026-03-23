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
        // Output formatting fix. Because of the `SCALE`, values should be normalized properly.
        // Wait, the guest code `scaled_p[v] = p[v] * (n as i64);`
        // But what was it previously returning?
        // Oh, wait! In f64 we returned `p.map(|val| val * (n as f64))`
        // But `val` was a fraction (0.0 to 1.0).
        // Here, `p[v]` is scaled by `SCALE`, so `p[v] * n` is scaled by `SCALE * n`? No, just scaled by SCALE.
        // Wait, look at `calculate_social_connectivity`:
        // base_p = SCALE / n. So the sum of p is SCALE.
        // When we do p * n, we get around SCALE.
        // But wait! If we do `p[v] * n`, and then divide by `SCALE as f64`, we should get numbers near 1.0.
        // So why is it 8389.5136?
        // Let's look at `base_p = fp_div(SCALE, n as i64)`.
        // `fp_div(SCALE, n) = (SCALE * SCALE) / n`.
        // THAT IS THE BUG.
        // I called `fp_div` to divide SCALE by n.
        // `fp_div(a, b)` does `(a * SCALE) / b`.
        // So `fp_div(SCALE, n)` did `(SCALE * SCALE) / n`. So it returned a double-scaled value!
        println!("  Agent {}: {:.4}", i, *val as f64 / SCALE as f64);
    }

    receipt.verify(METHOD_ID).unwrap();
    println!("\nReceipt verified successfully!");
}
