# `bb_tracker.py` Explained

## What This File Does

`bb_tracker.py` adds a custom branching rule to SCIP through PySCIPOpt. The rule does not actually choose branches itself. Instead, it records a snapshot of the branch-and-bound state each time SCIP reaches an LP-feasible branching point, then returns control to SCIP's normal branching logic.

The file has three main parts:

1. `BnBTracker`: a `Branchrule` subclass that collects metrics.
2. `_shannon_entropy(...)`: a helper used to summarize branching-candidate fractionality.
3. `track_and_solve(...)` plus the `__main__` demo: convenience code for attaching the tracker and running an example MIP.

## High-Level Flow

When you call `track_and_solve(model)`:

1. A `BnBTracker` object is created.
2. The tracker is registered with SCIP as a branching rule.
3. SCIP starts solving the model.
4. During solving:
   - `branchinit()` runs once at initialization and stores the original bounds of every variable.
   - `branchexeclp()` runs at LP branching points and records one snapshot of solver state.
5. After optimization finishes, the full snapshot history is returned as a list of dictionaries.

## `BnBTracker` Class

### Purpose

`BnBTracker` inherits from `pyscipopt.Branchrule`, which lets it plug into SCIP's branch-and-bound process.

### Internal State

The class stores:

- `self._history`: a list of recorded snapshots.
- `self._orig_bounds`: the original lower and upper bounds for each variable, used later to compute domain reduction.

### Public Methods

#### `get_state()`

Returns the most recent recorded snapshot, or `None` if nothing has been recorded yet.

#### `get_history()`

Returns a copy of the full history list.

## SCIP Callback Methods

### `branchinit()`

This runs once near the start of solving. It walks over all model variables and stores each variable's original bounds:

- `getLbOriginal()`
- `getUbOriginal()`

These values form the baseline for the domain-reduction metric later on.

### `branchexeclp(self, allowaddcons)`

This is the core callback. SCIP invokes it when it wants a branching rule to act on the current LP state.

Instead of branching, the method records six features:

1. `depth`
   - Current node depth in the search tree via `self.model.getDepth()`.

2. `nodes`
   - Number of explored nodes so far via `self.model.getNNodes()`.

3. `gap`
   - Current optimality gap via `self.model.getGap()`.

4. `cutoff_ratio`
   - Computed as `cuts_applied / max(nodes, 1)`.
   - `cuts_applied` comes from `self.model.getNCutsApplied()`.
   - This is used as a rough proxy for how aggressively cutting is happening relative to explored search.

5. `domain_reduction`
   - Computed by `_domain_reduction()`.
   - Measures how much variable domains have shrunk compared to their original spans.

6. `n_candidates` and `entropy`
   - `getLPBranchCands()` returns the current LP branching candidates and their fractionalities.
   - `n_candidates` is set to `nlp`, the number of LP branching candidates.
   - `entropy` summarizes the fractionalities with Shannon entropy.

After collecting the data, the method appends a dictionary like this:

```python
{
    "depth": depth,
    "nodes": nodes,
    "gap": gap,
    "cutoff_ratio": cutoff_ratio,
    "domain_reduction": domain_reduction,
    "n_candidates": n_candidates,
    "entropy": entropy,
}
```

Finally it returns:

```python
{"result": SCIP_RESULT.DIDNOTRUN}
```

That result is important: it tells SCIP this rule did not make a branching decision, so SCIP should continue with its normal branching behavior. In other words, this rule is an observer, not a controller.

## Helper: `_domain_reduction()`

This method computes the average amount of bound tightening across variables.

For each variable:

1. Look up the original bounds saved in `branchinit()`.
2. Compute the original span:

```python
orig_span = orig_ub - orig_lb
```

3. Compute the current local span:

```python
cur_span = var.getUbLocal() - var.getLbLocal()
```

4. Convert that into a reduction score:

```python
1.0 - cur_span / orig_span
```

Interpretation:

- `0.0` means no reduction.
- `1.0` means the domain has been fully tightened.
- Values in between indicate partial tightening.

The method averages this score over all variables with a valid positive original span.

## Helper: `_shannon_entropy(fracs)`

This function converts the list of branch-candidate fractionalities into a normalized distribution and computes Shannon entropy.

Why this is useful:

- Low entropy means the fractionalities are concentrated in a small part of the candidate set.
- High entropy means they are more spread out.

The function safely returns `0.0` when:

- there are no candidates, or
- the total fractionality is not positive.

## `track_and_solve(model, quiet=True)`

This is a convenience wrapper around the tracker lifecycle.

It:

1. Creates the tracker.
2. Registers it with very high priority.
3. Optionally hides solver output.
4. Calls `model.optimize()`.
5. Returns the recorded history.

The high priority matters because it increases the chance that the tracker callback runs before other branching rules. Since it returns `DIDNOTRUN`, SCIP can still continue with its default behavior afterward.

## Demo Block (`if __name__ == "__main__":`)

The bottom section builds a random multi-dimensional knapsack mixed-integer program to demonstrate the tracker.

### What the demo changes in SCIP

It deliberately disables or limits several solver features:

- cutting planes
- presolving
- primal heuristics
- total node count

This makes branch-and-bound activity easier to observe and keeps the demo runtime manageable.

### What model is created

- `n_items = 80`
- `n_knapsacks = 5`
- binary decision variables `x0, x1, ..., x79`
- one capacity constraint per knapsack
- a maximization objective using random item values

### What gets printed

After solving, the code prints a compact table where each row is one recorded snapshot. The columns match the metrics collected in `branchexeclp()`.

## Why This Design Works

The file is intentionally minimal:

- It reuses SCIP's callback system instead of modifying the solver.
- It gathers search-state features without interfering with the actual branching policy.
- It exposes both per-step access (`get_state`) and full-history access (`get_history`).

That makes it useful for logging, analysis, and downstream learning systems that want branch-and-bound state trajectories.

## One Important Detail

The tracker only records snapshots at LP branching callbacks. It does not record every internal solver event. So the history is a sequence of branching-point observations, not a full trace of all SCIP activity.
