import json
import os
from datetime import datetime
from typing import Dict, Any, List


class ExperimentTracker:
    """
    [EXPLANATORY: ExperimentTracker logs the parameters and outcomes of simulations.]
    [IDENTIFIER: ExperimentTracker]
    """

    def __init__(self, log_dir: str = "simulations/experiments"):
        """
        [EXPLANATORY: Initializes the experiment tracker and creates the log directory if needed.]
        [IDENTIFIER: __init__]
        """
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.experiments: List[Dict[str, Any]] = []

    def log_experiment(
        self, name: str, hypothesis: str, params: Dict[str, Any], metrics: Dict[str, Any], success: bool
    ):
        """
        [EXPLANATORY: Logs a single experiment run.]
        [IDENTIFIER: log_experiment]
        """
        experiment = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": name,
            "hypothesis": hypothesis,
            "parameters": params,
            "metrics": metrics,
            "success": bool(success),
        }
        self.experiments.append(experiment)

        # Save to JSON line
        json_path = os.path.join(self.log_dir, "experiments_log.jsonl")
        with open(json_path, "a") as f:
            f.write(json.dumps(experiment) + "\n")

    def export_config(self, params: Dict[str, Any], filename: str = "deploy_config.json"):
        """
        [EXPLANATORY: Exports successful parameters for use in Foundry.]
        [IDENTIFIER: export_config]
        """
        with open(filename, "w") as f:
            json.dump(params, f, indent=4)
