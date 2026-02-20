"""
Datacenter Configuration Package.

Provides configuration files and templates for the datacenter.
"""

from pathlib import Path

CONFIG_DIR = Path(__file__).parent
COLLECTORS_DIR = CONFIG_DIR / "collectors"

__all__ = ["CONFIG_DIR", "COLLECTORS_DIR"]
