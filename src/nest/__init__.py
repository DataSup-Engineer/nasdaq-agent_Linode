"""
NEST Integration for NASDAQ Stock Agent

This package provides integration with the NANDA NEST (Network of Autonomous 
Distributed Agents) framework, enabling agent-to-agent (A2A) communication 
while maintaining the existing FastAPI REST interface.
"""

from .config import NESTConfig
from .adapter import NESTAdapter

__all__ = ["NESTConfig", "NESTAdapter"]
