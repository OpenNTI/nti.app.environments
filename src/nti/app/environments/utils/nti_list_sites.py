#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import pprint
import argparse

from zope import component

from nti.app.environments.interfaces import IOnboardingServer

from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.utils import run_with_onboarding

logger = __import__('logging').getLogger(__name__)

def _do_list_sites(root):
    sites = get_sites_folder(root)

    for site in sites.values():
        print(site.id)

def main():
    arg_parser = argparse.ArgumentParser(description="List sites")
    arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
                                                    dest='verbose')
    arg_parser.add_argument('-c', '--config',
                            dest='config',
                            help="The config file",
                            required=True)
    
    args = arg_parser.parse_args()

    run_with_onboarding(settings=args.config,
                        verbose=args.verbose,
                        use_transaction_runner=True,
                        function=_do_list_sites)
    sys.exit(0)


if __name__ == '__main__':
    main()
