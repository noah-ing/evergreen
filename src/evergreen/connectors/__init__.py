"""
Connectors for external data sources.

Each connector handles authentication, data fetching, and delta sync for a specific source.
"""

from evergreen.connectors.base import BaseConnector
from evergreen.connectors.m365 import M365Connector

__all__ = ["BaseConnector", "M365Connector"]
