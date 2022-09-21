import yaml
import os

yaml_file = os.path.join(os.path.dirname(__file__), 'params.yaml')

with open(yaml_file, 'r') as y:
    configs = yaml.load(y, Loader=yaml.FullLoader)

print(configs)
print(os.path.exists(configs['data']['sde']['path']))
import pdb;pdb.set_trace()