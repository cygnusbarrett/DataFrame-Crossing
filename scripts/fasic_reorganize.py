#!/usr/bin/env python3
"""Atajo: dry-run / apply de reorganización FASIC."""

import sys

from consejos_guerra.cli import app

if __name__ == "__main__":
    app(["fasic-reorganize", *sys.argv[1:]])
