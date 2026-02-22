"""
LLM-Guided Dynamic Branching Rule Scheduler — Entry point.
"""

import argparse
import yaml


def main():
    parser = argparse.ArgumentParser(
        description="LLM-guided dynamic branching rule scheduling for B&B"
    )
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    print(f"Loaded config: {config}")
    # TODO: Initialize SCIP, LLM scheduler, run experiments


if __name__ == "__main__":
    main()
