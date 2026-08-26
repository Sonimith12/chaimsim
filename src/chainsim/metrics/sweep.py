"""ScenarioSweep: run parameter grids with Monte Carlo replications and collect tidy results.

To be implemented in Phase 2. Takes a base scenario, a parameter grid
(e.g. different lead times, different policies), and a number of Monte
Carlo replications; runs all combinations (vectorized with NumPy where
possible, e.g. batching demand generation across replications) and
returns a tidy results DataFrame.
"""
