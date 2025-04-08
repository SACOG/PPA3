UPDATED 4/8/2025

README FOR GLOBAL CONFIG FILES
The data_paths.yaml and parameters.py config files are used by at least several, if not all,
PPA GP tasks. HOWEVER, this folder only contains *copies* of them for record-keeping purposes and sharing purposes.

The versions actually used by PPA is specified in each GP tasks config_links.py script.
As of 2025 the used versions are on the PPA server machine.

This seems clunky but it means we can have all GP tasks point to just 2 config scripts, rather than
having separate versions for each GP task.