"""
B&B State Tracker — collects per-node search-state metrics from SCIP.

Implements the 6 features described in Section 4.2 / Figure 3 of
"LLM Guided Dynamic Branching Rule Scheduling in B&B":
  1. Depth
  2. Explored nodes
  3. Optimality gap
  4. Cutoff ratio
  5. Domain reduction strength
  6. Branching candidates + entropy
"""

from math import log2
from pyscipopt import Model, Branchrule, SCIP_RESULT


class BnBTracker(Branchrule):
    """Custom branching rule that records B&B state at every LP-feasible node."""

    def __init__(self):
        self._history: list[dict] = []
        self._orig_bounds: dict[str, tuple[float, float]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_state(self) -> dict | None:
        """Return the most recent state snapshot, or None."""
        return self._history[-1] if self._history else None

    def get_history(self) -> list[dict]:
        """Return all recorded snapshots."""
        return list(self._history)

    # ------------------------------------------------------------------
    # SCIP callback
    # ------------------------------------------------------------------
    def branchinit(self):
        """Cache original variable bounds once at the start of solving."""
        self._orig_bounds = {}
        for var in self.model.getVars():
            lb, ub = var.getLbOriginal(), var.getUbOriginal()
            self._orig_bounds[var.name] = (lb, ub)

    def branchexeclp(self, allowaddcons):
        # --- 1. Depth ---
        depth = self.model.getDepth()

        # --- 2. Explored nodes ---
        nodes = self.model.getNNodes()

        # --- 3. Optimality gap ---
        gap = self.model.getGap()

        # --- 4. Cutoff ratio (cuts applied / nodes as proxy) ---
        cuts_applied = self.model.getNCutsApplied()
        cutoff_ratio = cuts_applied / max(nodes, 1)

        # --- 5. Domain reduction strength ---
        domain_reduction = self._domain_reduction()

        # --- 6. Branching candidates + entropy ---
        cands, vals, fracs, nlp, nprio, nimpl = self.model.getLPBranchCands()
        n_candidates = nlp
        entropy = _shannon_entropy(fracs[:nlp])

        self._history.append({
            "depth":              depth,
            "nodes":              nodes,
            "gap":                gap,
            "cutoff_ratio":       cutoff_ratio,
            "domain_reduction":   domain_reduction,
            "n_candidates":       n_candidates,
            "entropy":            entropy,
        })

        # Let SCIP use its default branching rule
        return {"result": SCIP_RESULT.DIDNOTRUN}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _domain_reduction(self) -> float:
        """Average tightening: 1 - (cur_ub - cur_lb) / (orig_ub - orig_lb)."""
        total, count = 0.0, 0
        for var in self.model.getVars():
            orig = self._orig_bounds.get(var.name)
            if orig is None:
                continue
            orig_lb, orig_ub = orig
            span = orig_ub - orig_lb
            if span <= 0:
                continue
            cur_span = var.getUbLocal() - var.getLbLocal()
            total += 1.0 - cur_span / span
            count += 1
        return total / count if count else 0.0


def _shannon_entropy(fracs: list[float]) -> float:
    """Shannon entropy of fractionality values (treated as a distribution)."""
    if not fracs:
        return 0.0
    total = sum(fracs)
    if total <= 0:
        return 0.0
    ent = 0.0
    for f in fracs:
        p = f / total
        if p > 0:
            ent -= p * log2(p)
    return ent


# ------------------------------------------------------------------
# Convenience wrappers
# ------------------------------------------------------------------

def track_and_solve(model: Model, quiet: bool = True) -> list[dict]:
    """Attach a BnBTracker to *model*, solve, and return the snapshot history."""
    tracker = BnBTracker()
    model.includeBranchrule(
        tracker,
        name="BnBTracker",
        desc="Collects B&B state metrics per node",
        priority=10000000,   # high priority → called first, then DIDNOTRUN defers
        maxdepth=-1,
        maxbounddist=1.0,
    )
    if quiet:
        model.hideOutput()
    model.optimize()
    return tracker.get_history()


# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------

if __name__ == "__main__":
    import random

    random.seed(42)

    # Build a multi-dimensional knapsack MIP that forces real B&B exploration.
    # Disable cuts and heuristics so the solver must actually branch.
    n_items = 80
    n_knapsacks = 5
    m = Model("multi_knapsack")

    m.setParam("separating/maxrounds", 0)      # no cutting planes
    m.setParam("separating/maxroundsroot", 0)
    m.setParam("presolving/maxrounds", 0)       # no presolving
    m.setHeuristics(0)                           # disable primal heuristics
    m.setParam("limits/nodes", 200)             # cap nodes for demo speed

    weights = [[random.randint(1, 30) for _ in range(n_items)]
               for _ in range(n_knapsacks)]
    values = [random.randint(1, 100) for _ in range(n_items)]
    capacities = [int(0.4 * sum(row)) for row in weights]

    xs = [m.addVar(f"x{i}", vtype="B") for i in range(n_items)]

    for k in range(n_knapsacks):
        m.addCons(sum(weights[k][i] * xs[i] for i in range(n_items))
                  <= capacities[k])
    m.setObjective(sum(values[i] * xs[i] for i in range(n_items)), "maximize")

    history = track_and_solve(m, quiet=True)

    # Print a compact table
    header = f"{'#':>4}  {'depth':>5}  {'nodes':>6}  {'gap':>8}  {'cutoff':>8}  {'domred':>8}  {'cands':>5}  {'entropy':>8}"
    print(header)
    print("-" * len(header))
    for i, s in enumerate(history):
        print(
            f"{i:4d}  {s['depth']:5d}  {s['nodes']:6d}  "
            f"{s['gap']:8.4f}  {s['cutoff_ratio']:8.4f}  "
            f"{s['domain_reduction']:8.4f}  {s['n_candidates']:5d}  "
            f"{s['entropy']:8.4f}"
        )
    print(f"\nTotal snapshots: {len(history)}")
