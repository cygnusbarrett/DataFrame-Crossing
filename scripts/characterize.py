#!/usr/bin/env python3
"""Atajo: caracterizar el dataset de Consejos de Guerra."""

from consejos_guerra.cli import app

if __name__ == "__main__":
    app(["characterize", *(__import__("sys").argv[1:])])
