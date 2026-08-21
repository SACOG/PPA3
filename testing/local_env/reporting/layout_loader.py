import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT_DIR = os.path.join(HERE, "layout")


def load_layout(service):
    path = os.path.join(LAYOUT_DIR, f"{service}.yaml")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
