"""SupplyChainEnv: a Gymnasium-compatible environment wrapping the simulation engine.

To be implemented in Phase 3. Observation space: per-node inventory,
pipeline/in-transit quantities, backlog, and a configurable window of
recent demand history. Action space: order quantities per controllable
node, supporting both discrete and continuous spaces via a config flag.
Reward: negative total cost per step (configurable weighting between
holding, backlog, and transportation cost). Must pass
`gymnasium.utils.env_checker.check_env()`.
"""
