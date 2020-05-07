#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
import os
import sys
import pprint
import argparse

import tabulate

import gevent
from gevent.pool import Pool

from zope import component

from nti.app.environments.api.siteinfo import NTClient

from nti.app.environments.interfaces import IOnboardingServer

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.utils import run_with_onboarding

logger = __import__('logging').getLogger(__name__)

def _ping_site(siteid):
    server = component.getUtility(IOnboardingServer)

    # Open our very own connection
    conn = server.root_database.open()
    try:
        # Load our site
        root = server.root_onboarding_folder(conn)
        site = get_sites_folder(root)[siteid]

        #Build a client we can ping with
        client = NTClient()
        dns = site.dns_names[0]
        site_name = None
        if dns:
            logger.info('Pinging site %s at %s', siteid, dns)
            resp = client.dataserver_ping(dns) #grr we lose access to the status code
            logger.info('Pinged site %s at %s', siteid, dns)
            if resp:
                site_name = resp.get('Site', None)
        return siteid, dns, site_name
        
    finally:
        conn.close()    

def _do_ping_sites(root, pool_size=5):
    pool = Pool(pool_size)
    rows = pool.map(_ping_site, [site.__name__ for site in get_sites_folder(root).values()
                                 if site.status == SITE_STATUS_ACTIVE])
    print(tabulate.tabulate(rows, headers=['ID', 'DNS', 'DS Site']))
            

def main():
    arg_parser = argparse.ArgumentParser(description="Ping sites")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                                                    dest='verbose')
    arg_parser.add_argument('-c', '--config',
                            dest='config',
                            help="The config file",
                            required=True)

    arg_parser.add_argument('-p', '--pool-size',
                            dest='pool_size',
                            type=int,
                            default=5)
    
    args = arg_parser.parse_args()

    run_with_onboarding(settings=args.config,
                        verbose=args.verbose,
                        use_transaction_runner=False,
                        function=_do_ping_sites)
    sys.exit(0)


if __name__ == '__main__':
    main()
