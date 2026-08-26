"""Pydantic models for scenario and network configuration.

To be implemented alongside the domain layer. All scenario configs, node
configs, and policy configs are defined as `pydantic.BaseModel` subclasses
so they can be loaded from YAML/JSON and validated automatically.
"""
