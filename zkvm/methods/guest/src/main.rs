use risc0_zkvm::guest::env;
use serde::{Deserialize, Serialize};

const SCALE: i64 = 10_000;
const MAX_NODES: usize = 8;

#[derive(Serialize, Deserialize)]
pub struct TrustInput {
    pub interactions: Vec<Vec<i64>>, // Scaled adjacency matrix, expected size <= MAX_NODES
}

#[derive(Serialize, Deserialize)]
pub struct TrustOutput {
    pub transitive_trust: Vec<i64>,
    pub social_connectivity: Vec<i64>,
}

// --- Fixed-Point Math Helpers (Strictly i64) ---
fn fp_mul(a: i64, b: i64) -> i64 {
    (a * b) / SCALE
}

fn fp_div(a: i64, b: i64) -> i64 {
    if b == 0 { return 0; }
    (a * SCALE) / b
}

fn fp_sqrt(a: i64) -> i64 {
    // Preserve dimensionality by scaling before the root
    let scaled = a * SCALE;
    scaled.isqrt()
}
// --------------------------------

fn calculate_transitive_trust(interactions: &[[i64; MAX_NODES]; MAX_NODES], n: usize) -> [i64; MAX_NODES] {
    let mut e = [SCALE; MAX_NODES];
    let iterations = 5;

    let mut normalized_interactions = [[0; MAX_NODES]; MAX_NODES];

    for u in 0..n {
        let mut total = 0;
        let mut sqrt_weights = [0; MAX_NODES];
        for v in 0..n {
            let weight = interactions[u][v];
            if weight > 0 {
                let sqrt_w = fp_sqrt(weight);
                sqrt_weights[v] = sqrt_w;
                total += sqrt_w;
            }
        }
        if total > 0 {
            for v in 0..n {
                normalized_interactions[u][v] = fp_div(sqrt_weights[v], total);
            }
        }
    }

    for _ in 0..iterations {
        let mut new_e = [0; MAX_NODES];
        for u in 0..n {
            for v in 0..n {
                new_e[v] += fp_mul(e[u], normalized_interactions[u][v]);
            }
        }

        let mut total_e: i64 = 0;
        for v in 0..n {
            total_e += new_e[v];
        }

        if total_e > 0 {
            let target_sum = (n as i64) * SCALE;
            for v in 0..n {
                e[v] = (new_e[v] * target_sum) / total_e;
            }
        } else {
            for v in 0..n {
                e[v] = new_e[v];
            }
        }
    }
    e
}

fn calculate_social_connectivity(interactions: &[[i64; MAX_NODES]; MAX_NODES], n: usize) -> [i64; MAX_NODES] {
    // BUG FIX: `fp_div(SCALE, n as i64)` double scales because fp_div scales the numerator again.
    // The fraction we want is `1.0 / n`, which in fixed point is `SCALE / n`.
    let base_p = SCALE / (n as i64);
    let mut p = [base_p; MAX_NODES];
    let d: i64 = 8_500; // 0.85 * SCALE
    let iterations = 10;

    let mut normalized_interactions = [[0; MAX_NODES]; MAX_NODES];
    let mut sink_flags = [false; MAX_NODES];

    for u in 0..n {
        let mut out_degree = 0;
        for v in 0..n {
            out_degree += interactions[u][v];
        }
        if out_degree > 0 {
            for v in 0..n {
                normalized_interactions[u][v] = fp_div(interactions[u][v], out_degree);
            }
        } else {
            sink_flags[u] = true;
        }
    }

    for _ in 0..iterations {
        let mut sink_contribution = 0;
        // Same bug: SCALE - d is already scaled. To get (1-d)/n, we do (SCALE - d) / n
        let p_reset = (SCALE - d) / (n as i64);
        let mut new_p = [p_reset; MAX_NODES];

        for u in 0..n {
            let p_u_d = fp_mul(p[u], d);
            for v in 0..n {
                new_p[v] += fp_mul(p_u_d, normalized_interactions[u][v]);
            }
        }

        for u in 0..n {
            if sink_flags[u] {
                // Here we want d * (p[u] / n). But p[u] / n is a simple division, not fp_div!
                // Wait, if p[u] is scaled, p[u]/n is also scaled. So we can just do p[u] / n.
                let p_u_n = p[u] / (n as i64);
                sink_contribution += fp_mul(d, p_u_n);
            }
        }

        if sink_contribution > 0 {
            for v in 0..n {
                new_p[v] += sink_contribution;
            }
        }
        for v in 0..n {
            p[v] = new_p[v];
        }
    }

    let mut scaled_p = [0; MAX_NODES];
    for v in 0..n {
        scaled_p[v] = p[v] * (n as i64);
    }
    scaled_p
}

fn main() {
    let input: TrustInput = env::read();
    let n = input.interactions.len();

    if n == 0 || n > MAX_NODES {
        env::commit(&TrustOutput { transitive_trust: vec![], social_connectivity: vec![] });
        return;
    }

    let mut interactions = [[0; MAX_NODES]; MAX_NODES];
    for i in 0..n {
        for j in 0..n {
            interactions[i][j] = input.interactions[i][j];
        }
    }

    let transitive_trust_arr = calculate_transitive_trust(&interactions, n);
    let social_connectivity_arr = calculate_social_connectivity(&interactions, n);

    let output = TrustOutput {
        transitive_trust: transitive_trust_arr[0..n].to_vec(),
        social_connectivity: social_connectivity_arr[0..n].to_vec(),
    };

    env::commit(&output);
}
