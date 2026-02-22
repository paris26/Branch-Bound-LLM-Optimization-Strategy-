# LLM-Guided Dynamic Branching Rule Scheduling in Branch-and-Bound

> Under review at ICLR 2026 (double-blind)

## Overview

This project implements an LLM-guided approach to dynamically schedule branching rules throughout the Branch-and-Bound (B&B) process for solving Mixed Integer Linear Programs (MILPs).

### Key Idea
- **Initial stage**: LLM selects an appropriate starting branching rule based on problem type and scale
- **During solving**: LLM monitors the evolving search tree state and adaptively decides when and which rule to switch to
- **Zero-shot generalization** across diverse problem types — no training pipeline required

## Architecture

```
src/
├── scheduler/       # LLM-based branching rule scheduler
├── prompts/         # Prompt templates (initial selection + switching)
├── scip_plugin/     # SCIP solver integration
├── benchmarks/      # Benchmark problem generators
└── evaluation/      # Metrics and evaluation scripts

configs/             # Experiment configurations
results/             # Experimental results and logs
tests/               # Unit and integration tests
docs/                # Documentation and notes
```

## Branching Rules Supported
- **Fullstrong** — strong branching (high quality, high cost)
- **Pseudocost** — history-based estimation (efficient after warm-up)
- **Most Infeasible** — selects variable closest to 0.5
- **Reliability** — adaptive hybrid of strong + pseudocost
- **Relpscost** — SCIP's default rule

## Benchmark Problems
- Set Covering
- Combinatorial Auctions
- Capacitated Facility Location
- Maximum Independent Set

## Requirements
- Python 3.10+
- [PySCIPOpt](https://github.com/scipopt/PySCIPOpt)
- OpenAI API (or compatible LLM endpoint)

## Setup
```bash
pip install -r requirements.txt
```

## Usage
```bash
python src/main.py --config configs/default.yaml
```

## Citation
Paper under double-blind review — citation to be added upon acceptance.

## License
MIT
