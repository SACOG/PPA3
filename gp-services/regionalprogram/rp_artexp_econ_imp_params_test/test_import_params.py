from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
import parameters as params

print(f"success - test value = {params.region_fc}")