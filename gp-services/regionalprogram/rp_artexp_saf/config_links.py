from pathlib import Path
import sys
import yaml

# =============================================================================
# VERSION: Task 5 local/testing build — branch data_layer_update
#
# config_dir is pointing at the LOCAL REPO copy of globalconfig_rp so that the
# Task 5 constants added to parameters.py are available without a server-side
# file deployment.  The production server copy at the path below does NOT yet
# have these constants:
#   col_collision_type, collision_type_labels,
#   col_pcf_category, pcf_category_labels, colln_type_top_n
#
# TO CONNECT TO PRODUCTION SERVER:
#   1. Copy globalconfig_rp/parameters.py to the server:
#      \\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig\
#   2. Swap config_dir below — comment out the local line, uncomment server line.
# =============================================================================

# PRODUCTION (uncomment after step 1 above):
# config_dir = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig'

# LOCAL / TESTING (active — Task 5 branch):
config_dir = r'C:\Users\tenoru\Downloads\PPA3\gp-services\regionalprogram\globalconfig_rp'

#===================================================================
# load parameters py file
sys.path.append(config_dir)
import parameters as params # Must keep this import; needs to be part of script namespace when used by other scripts!

# load yaml config as dict
cfg_yaml = Path(config_dir).joinpath('data_paths.yaml')
with open(cfg_yaml, 'r') as y:
    cfg = yaml.load(y, Loader=yaml.FullLoader)
