use nalgebra::{DMatrix, DVector};
use risc0_zkvm::guest::env;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct TrustInput {
    pub interactions: Vec<Vec<f64>>, // Adjacency matrix of interactions
}

#[derive(Serialize, Deserialize)]
pub struct TrustOutput {
    pub transitive_trust: Vec<f64>,
    pub social_connectivity: Vec<f64>,
}

fn calculate_transitive_trust(interactions: &DMatrix<f64>) -> DVector<f64> {
    let n = interactions.nrows();
    let mut e = DVector::from_element(n, 1.0);
    let iterations = 5;

    // Normalize interactions (Square root of weights as in Python)
    let mut normalized_interactions = DMatrix::zeros(n, n);
    for u in 0..n {
        let mut total = 0.0;
        let mut sqrt_weights = vec![0.0; n];
        for v in 0..n {
            let weight = interactions[(u, v)];
            if weight > 0.0 {
                let sqrt_w = weight.sqrt();
                sqrt_weights[v] = sqrt_w;
                total += sqrt_w;
            }
        }
        if total > 0.0 {
            for v in 0..n {
                normalized_interactions[(u, v)] = sqrt_weights[v] / total;
            }
        }
    }

    // Power iterations
    for _ in 0..iterations {
        let mut new_e = DVector::zeros(n);
        for u in 0..n {
            for v in 0..n {
                new_e[v] += e[u] * normalized_interactions[(u, v)];
            }
        }

        let total_e: f64 = new_e.iter().sum();
        if total_e > 0.0 {
            let scale = n as f64 / total_e;
            e = new_e.map(|val| val * scale);
        } else {
            e = new_e;
        }
    }

    e
}

fn calculate_social_connectivity(interactions: &DMatrix<f64>) -> DVector<f64> {
    let n = interactions.nrows();
    let mut p = DVector::from_element(n, 1.0 / (n as f64));
    let d = 0.85;
    let iterations = 10;

    // Normalize interactions based on out-degree
    let mut normalized_interactions = DMatrix::zeros(n, n);
    let mut sink_ids = Vec::new();
    for u in 0..n {
        let mut out_degree = 0.0;
        for v in 0..n {
            out_degree += interactions[(u, v)];
        }
        if out_degree > 0.0 {
            for v in 0..n {
                normalized_interactions[(u, v)] = interactions[(u, v)] / out_degree;
            }
        } else {
            sink_ids.push(u);
        }
    }

    // PageRank iterations
    for _ in 0..iterations {
        let mut sink_contribution = 0.0;
        let mut new_p = DVector::from_element(n, (1.0 - d) / (n as f64));

        for u in 0..n {
            let p_u_d = p[u] * d;
            for v in 0..n {
                new_p[v] += p_u_d * normalized_interactions[(u, v)];
            }
        }

        for &u in &sink_ids {
            sink_contribution += d * (p[u] / (n as f64));
        }

        if sink_contribution > 0.0 {
            for v in 0..n {
                new_p[v] += sink_contribution;
            }
        }

        p = new_p;
    }

    // Scale to meaningful values roughly matching E
    p.map(|val| val * (n as f64))
}

fn main() {
    // 1. Read input from host
    let input: TrustInput = env::read();

    let n = input.interactions.len();
    if n == 0 {
        let output = TrustOutput {
            transitive_trust: vec![],
            social_connectivity: vec![],
        };
        env::commit(&output);
        return;
    }

    // Convert Vec<Vec<f64>> to DMatrix
    let mut interactions = DMatrix::zeros(n, n);
    for i in 0..n {
        for j in 0..n {
            interactions[(i, j)] = input.interactions[i][j];
        }
    }

    // 2. Perform Trust Calculations
    let transitive_trust = calculate_transitive_trust(&interactions);
    let social_connectivity = calculate_social_connectivity(&interactions);

    // 3. Prepare and Commit Output
    let output = TrustOutput {
        transitive_trust: transitive_trust.as_slice().to_vec(),
        social_connectivity: social_connectivity.as_slice().to_vec(),
    };

    env::commit(&output);
}
