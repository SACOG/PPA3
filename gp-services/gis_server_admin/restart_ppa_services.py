"""
Name: restart_ppa_services.py
Purpose: Quick way to restart all PPA GP services, e.g., if making updates to various scripts
    and do not want to restart individually


Author: Darren Conly
Last Updated: Jul 2025
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""
from pathlib import Path
import re
from collections import namedtuple

from arcgis.gis import GIS
import arcgis.gis.admin as gisadmin

def connect(auth_file):
    # Creates connection to ESRI's GIS API for python.

    authdict = {}
    try:
        with open(auth_file, 'r') as f:
            rows = f.readlines()
            for row in rows:
                rs = row.strip('\n').split('=')
                authdict[rs[0].strip("\'")] = rs[1].strip("\'")
    except FileNotFoundError:
        raise Exception(f"PERMISSION ERROR: {auth_file} not found.")

    gisconn = GIS(authdict['portal_url'], authdict['user_name'], verify_cert=False)
    print("connection made to gis object.")

    GISConn = namedtuple('GISConn', 'auth conn')
    conn_obj = GISConn(auth=authdict, conn=gisconn)

    return conn_obj


def restart_services(gis_conn, search_exp='.*'):
    # Restarts all GP services in server specified in gis_conn if service name has regex-based match with search_exp.
    # Reference: https://support.esri.com/en-us/knowledge-base/how-to-stop-gis-services-using-arcgis-api-for-python-000019994

    servers = gis_conn.conn.admin.servers.list()
    svr_list = [s for s in servers if s.url == gis_conn.auth['svr_url']]
    if len(svr_list) > 0:
        svr = svr_list[0]
    else:
        raise Exception(f"ERROR: server url {gis_conn.auth['svr_url']} not found among available servers.")
        
    for svc in svr.services.list():
        svcname = svc.properties['serviceName']
        if svc.properties['type'] == 'GPServer' and re.match(search_exp, svcname):
            print(f"restarting {svcname}")
            svc.restart()
            
    print("Complete. All services restarted.")


if __name__ == '__main__':
    authorization_file = Path(__file__).parent.joinpath('gis_admin.auth')

    # regex. Use '.*' to run through all services, or alternative regex to filter
    # common expressions: 'CD.*' to only do community design, 'RP.*' to only do regional program, etc.
    search_string = 'RP.*'

    #==============RUN SCRIPT==============

    connection = connect(authorization_file)
    restart_services(connection, search_exp=search_string)