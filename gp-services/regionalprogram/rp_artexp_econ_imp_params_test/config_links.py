from pathlib import Path
import sys
import yaml

# set path to global configuration files
config_dir = r'\\Arcserverppa-svr\PPA_SVR\PPA_03_01\RegionalProgram\globalconfig'

#===================================================================
# load parameters py file
sys.path.append(config_dir)
import parameters as params

# load yaml config as dict
cfg_yaml = Path(config_dir).joinpath('data_paths.yaml')
with open(cfg_yaml, 'r') as y:
    cfg = yaml.load(y, Loader=yaml.FullLoader)