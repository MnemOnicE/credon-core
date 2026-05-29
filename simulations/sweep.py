import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from simulations.engine import Engine
from simulations.experiment_tracker import ExperimentTracker

# Ensure output directory exists
os.makedirs("docs/results", exist_ok=True)

tracker = ExperimentTracker()


def sweep_leverage():
    """
    [EXPLANATORY: sweep_leverage]
    [IDENTIFIER: sweep_leverage]
    """
    print("Sweeping L/B Ratios...")
    b_value = 500
    l_values = range(100, 900, 100)
    epochs = 20

    all_results = []
    divergence_data = {100: None, 400: None, 800: None}

    best_l = None
    best_spread = -float("inf")

    for l_val in l_values:
        print(f"Running simulation for L={l_val}, B={b_value}")
        engine = Engine(num_honest=20, num_malicious=5)
        engine.B = b_value
        engine.L = l_val

        success = True
        try:
            for _ in range(epochs):
                engine.run_epoch()
        except Exception as e:
            success = False
            print(f"Simulation failed for L={l_val}: {e}")

        results = engine.get_results()
        df = pd.DataFrame(results)
        df["L"] = l_val
        all_results.append(df)

        if l_val in divergence_data:
            divergence_data[l_val] = df

        final_epoch = df.iloc[-1]
        spread = final_epoch["avg_h_roi"] - final_epoch["avg_m_roi"]

        # Consider successful if honest ROI > malicious ROI
        is_favorable = spread > 0

        metrics = {
            "final_honest_roi": float(final_epoch["avg_h_roi"]),
            "final_malicious_roi": float(final_epoch["avg_m_roi"]),
            "roi_spread": float(spread),
            "final_honest_trust": float(final_epoch["avg_h_trust"]),
            "final_malicious_trust": float(final_epoch["avg_m_trust"]),
        }

        tracker.log_experiment(
            name="sweep_leverage",
            hypothesis=f"Testing L={l_val} with B={b_value} to see if honest actors outperform malicious ones.",
            params={"L": l_val, "B": b_value, "epochs": epochs},
            metrics=metrics,
            success=success and is_favorable,
        )

        if success and is_favorable and spread > best_spread:
            best_spread = spread
            best_l = l_val

    if best_l is not None:
        print(f"Best leverage found: L={best_l}. Exporting config.")
        config_path = "deploy_config.json"
        config = {}
        if os.path.exists(config_path):
            import json
            with open(config_path, "r") as f:
                config = json.load(f)
        config["L"] = best_l
        config["B"] = b_value
        tracker.export_config(config)

    combined_df = pd.concat(all_results, ignore_index=True)

    # Chart 1
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

    # Chart 2
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    fig.suptitle("Trust Score Divergence Over Time")
    for i, l_val in enumerate([100, 400, 800]):
        df = divergence_data[l_val]
        ax = axes[i]
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
    print("Leverage sweep complete.")


def sweep_reward_rate():
    """
    [EXPLANATORY: sweep_reward_rate]
    [IDENTIFIER: sweep_reward_rate]
    """
    print("Sweeping Reward Release Rate (rho)...")
    rho_values = [0.01, 0.05, 0.10, 0.20]
    epochs = 20

    all_results = []

    best_rho = None
    best_metric = -float("inf")

    for rho in rho_values:
        print(f"Running simulation for rho={rho}")
        engine = Engine(num_honest=20, num_malicious=5)
        engine.rho = rho

        success = True
        try:
            for _ in range(epochs):
                engine.run_epoch()
        except Exception as e:
            success = False
            print(f"Simulation failed for rho={rho}: {e}")

        results = engine.get_results()
        df = pd.DataFrame(results)
        if df.empty:
            continue
        df["rho"] = rho
        all_results.append(df)

        final_epoch = df.iloc[-1]

        # Determine success (e.g., supply doesn't explode, trust remains stable)
        supply_growth = final_epoch["circulating_supply"] / df.iloc[0]["circulating_supply"]
        is_stable = supply_growth < 5.0  # Arbitrary stability check

        metrics = {
            "final_circulating_supply": float(final_epoch["circulating_supply"]),
            "supply_growth_ratio": float(supply_growth),
        }

        tracker.log_experiment(
            name="sweep_reward_rate",
            hypothesis=f"Testing rho={rho} to find optimal inflation rate that preserves token value.",
            params={"rho": rho, "epochs": epochs},
            metrics=metrics,
            success=success and is_stable,
        )

        if success and is_stable and metrics["final_circulating_supply"] > best_metric:
            best_metric = metrics["final_circulating_supply"]
            best_rho = rho

    if best_rho is not None:
        print(f"Best rho found: rho={best_rho}. Updating config.")

        # Read existing or create new config
        config_path = "deploy_config.json"
        config = {}
        if os.path.exists(config_path):
            import json

            with open(config_path, "r") as f:
                config = json.load(f)

        config["rho"] = best_rho
        tracker.export_config(config)

    combined_df = pd.concat(all_results, ignore_index=True)

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
    print("Reward Rate sweep complete.")


if __name__ == "__main__":
    sweep_leverage()
    sweep_reward_rate()
