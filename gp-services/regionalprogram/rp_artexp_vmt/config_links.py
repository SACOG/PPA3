from pathlib import Path
import os
import sys
import yaml

# Config directory. Defaults to the production server globalconfig.
# Set PPA3_LOCAL_CONFIG to a local globalconfig dir (parameters.py + data_paths.yaml)
# to redirect this subreport at local test data. Unset => production, unchanged.
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