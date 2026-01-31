#!/usr/bin/env python
"""
Engram - The Black Box Flight Recorder for Autonomous Systems
Entry point script
"""

import sys
from agent_forge.cli.engram import cli

if __name__ == '__main__':
    sys.exit(cli())
