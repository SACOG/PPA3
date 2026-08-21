"""Candidate-line registry shared by setup, health checks, and the browser form."""

import json
import os

import config


REGISTRY_PATH = os.path.join(str(config.HERE), "samples", "lines.json")


def load(root=None):
    root = os.path.abspath(root or str(config.local_root()))
    with open(REGISTRY_PATH, encoding="utf-8") as stream:
        raw = json.load(stream)
    lines = {}
    for key, original in raw.items():
        entry = dict(original)
        local_name = entry.get("local_name", key)
        entry["fc_path"] = os.path.join(root, "PPA3Testing.gdb", local_name)
        entry.setdefault("display_name", key)
        lines[key] = entry
    return lines
