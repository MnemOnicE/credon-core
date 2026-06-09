import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import concurrent.futures

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from simulations.engine import Engine

# Ensure output directory exists
os.makedirs("docs/results", exist_ok=True)


def run_leverage_sim(l_val, b_value=500, epochs=20):
    """
    [EXPLANATORY: helper to run a single leverage simulation]
    [IDENTIFIER: run_leverage_sim]
    [DIRECTIONAL: val]
    """
    print(f"Running simulation for L={l_val}, B={b_value}")
    engine = Engine(num_honest=20, num_malicious=5)
    engine.B = b_value
    engine.L = l_val

    for _ in range(epochs):
        engine.run_epoch()

    results = engine.get_results()
    df = pd.DataFrame(results)
    df["L"] = l_val
    return l_val, df


def sweep_leverage():
    """
    [EXPLANATORY: sweep_leverage]
    [IDENTIFIER: sweep_leverage]
    [DIRECTIONAL: val]
    """
    print("Sweeping L/B Ratios...")
    b_value = 500
    l_values = range(100, 900, 100)
    epochs = 20

    all_results = []
    divergence_data = {100: None, 400: None, 800: None}

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = {executor.submit(run_leverage_sim, l_val, b_value, epochs): l_val for l_val in l_values}
        for future in concurrent.futures.as_completed(futures):
            l_val, df = future.result()
            all_results.append(df)
            if l_val in divergence_data:
                divergence_data[l_val] = df

    combined_df = pd.concat(all_results, ignore_index=True)

    # Chart 1: Average Attacker ROI vs Average Honest ROI across L/B ratios at the final epoch
    final_epoch_data = combined_df[combined_df["epoch"] == epochs]

    plt.figure(figsize=(10, 6))
    sns.lineplot(data=final_epoch_data, x="L", y="avg_h_roi", label="Honest ROI", marker="o")
    sns.lineplot(data=final_epoch_data, x="L", y="avg_m_roi", label="Attacker ROI", marker="s")

    plt.title("Average ROI vs Loan Size (B=500)")
    plt.xlabel("Loan Amount (L)")
    plt.ylabel("Average ROI (CRE)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("docs/results/roi_vs_leverage.png")
    plt.close()

    # Chart 2: Trust Score Divergence (L=100, L=400, L=800)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    fig.suptitle("Trust Score Divergence Over Time")

    for i, l_val in enumerate([100, 400, 800]):
        df = divergence_data[l_val]
        ax = axes[i]
        # Sort by epoch to ensure lines are drawn correctly since results came in async
        df = df.sort_values(by="epoch")
        sns.lineplot(data=df, x="epoch", y="avg_h_trust", label="Honest Trust", ax=ax, marker="o")
        sns.lineplot(
            data=df,
            x="epoch",
            y="avg_m_trust",
            label="Malicious Trust",
            ax=ax,
            marker="s",
        )
        ax.set_title(f"Loan = {l_val}")
        ax.set_xlabel("Epoch")
        if i == 0:
            ax.set_ylabel("Average Trust Score")
        else:
            ax.set_ylabel("")
        ax.grid(True)
        ax.legend()

    plt.tight_layout()
    plt.savefig("docs/results/trust_divergence.png")
    plt.close()
    print("Leverage sweep complete. Artifacts saved to docs/results/")

    # Calculate optimal L
    # Optimal L is where honest ROI is maximized while minimizing attacker ROI
    # We can define a metric: difference between honest ROI and attacker ROI
    final_epoch_data_copy = final_epoch_data.copy()
    final_epoch_data_copy["roi_diff"] = final_epoch_data_copy["avg_h_roi"] - final_epoch_data_copy["avg_m_roi"]
    optimal_row = final_epoch_data_copy.loc[final_epoch_data_copy["roi_diff"].idxmax()]
    optimal_l = int(optimal_row["L"])

    return optimal_l, b_value


def run_reward_sim(rho, epochs=20):
    """
    [EXPLANATORY: helper to run a single reward rate simulation]
    [IDENTIFIER: run_reward_sim]
    [DIRECTIONAL: val]
    """
    print(f"Running simulation for rho={rho}")
    engine = Engine(num_honest=20, num_malicious=5)
    engine.rho = rho

    for _ in range(epochs):
        engine.run_epoch()

    results = engine.get_results()
    df = pd.DataFrame(results)
    df["rho"] = rho
    return rho, df


def sweep_reward_rate():
    """
    [EXPLANATORY: sweep_reward_rate]
    [IDENTIFIER: sweep_reward_rate]
    [DIRECTIONAL: val]
    """
    print("Sweeping Reward Release Rate (rho)...")
    rho_values = [0.01, 0.05, 0.10, 0.20]
    epochs = 20

    all_results = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = {executor.submit(run_reward_sim, rho, epochs): rho for rho in rho_values}
        for future in concurrent.futures.as_completed(futures):
            rho, df = future.result()
            all_results.append(df)

    combined_df = pd.concat(all_results, ignore_index=True)
    # Sort to ensure smooth plotting
    combined_df = combined_df.sort_values(by=["rho", "epoch"])

    # Plot Circulating Supply over time for different rhos
    plt.figure(figsize=(10, 6))
    sns.lineplot(
        data=combined_df,
        x="epoch",
        y="circulating_supply",
        hue="rho",
        marker="o",
        palette="tab10",
    )

    plt.title("Circulating Supply vs Time for different Reward Rates (rho)")
    plt.xlabel("Epoch")
    plt.ylabel("Circulating Supply (CRE)")
    plt.legend(title="Reward Rate (rho)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("docs/results/circulating_supply_vs_rho.png")
    plt.close()
    print("Reward Rate sweep complete. Artifacts saved to docs/results/")

    # Calculate optimal rho
    # For rho, perhaps the one that gives the highest stable circulating supply, or median value.
    # Let's say optimal rho is 0.05 by default, but let's calculate the one that gives max supply at final epoch
    # without exploding. We'll pick the one with the highest circulating supply at the end for simplicity,
    # or just the standard 0.05 if we want a moderate value.
    # Actually, a common goal is stable growth. Let's maximize circulating supply.
    final_epoch_data = combined_df[combined_df["epoch"] == epochs]
    optimal_row = final_epoch_data.loc[final_epoch_data["circulating_supply"].idxmax()]
    optimal_rho = float(optimal_row["rho"])

    return optimal_rho


if __name__ == "__main__":
    optimal_l, b_value = sweep_leverage()
    optimal_rho = sweep_reward_rate()

    config = {"OPTIMAL_L": optimal_l, "OPTIMAL_B": b_value, "OPTIMAL_RHO": optimal_rho}

    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "deploy_config.json"))
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"Optimal parameters exported to {config_path}")
