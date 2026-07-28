from pathlib import Path
import sys
import os
import yaml

# =============================================================================
# VERSION: Task 4 — rolled onto the PPA3_LOCAL_CONFIG env-var switch.
#
# Set PPA3_LOCAL_CONFIG to a local globalconfig dir (parameters.py + data_paths.yaml)
# to redirect this subreport at local test data. Unset => production, unchanged.
#
# NOTE (carried over from the Task 5 local/testing build): the PRODUCTION server
# copy of parameters.py at the path below does NOT yet have the Task 5 collision
# constants deployed:
#   col_collision_type, collision_type_labels,
#   col_pcf_category, pcf_category_labels, colln_type_top_n
# These must be deployed to the server's globalconfig before prod-mode runs of
# this subreport will have them available.
# =============================================================================
_PROD_CONFIG = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig'
config_dir = os.environ.get('PPA3_LOCAL_CONFIG') or _PROD_CONFIG

#===================================================================
# load parameters py file
sys.path.append(config_dir)
import parameters as params # Must keep this import; needs to be part of script namespace when used by other scripts!

# load yaml config as dict
cfg_yaml = Path(config_dir).joinpath('data_paths.yaml')
with open(cfg_yaml, 'r') as y:
    cfg = yaml.load(y, Loader=yaml.FullLoader)
