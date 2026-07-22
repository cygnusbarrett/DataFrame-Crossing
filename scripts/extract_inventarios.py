#!/usr/bin/env python3
"""Atajo: extraer inventarios Word."""

import sys

from consejos_guerra.cli import app

if __name__ == "__main__":
    app(["inventarios", *sys.argv[1:]])
