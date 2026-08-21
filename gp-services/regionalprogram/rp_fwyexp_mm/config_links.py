from pathlib import Path
import sys
import os
import yaml

# set path to global configuration files
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
