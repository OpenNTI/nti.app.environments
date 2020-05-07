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

from nti.app.environments.utils import run_as_onboarding_main

logger = __import__('logging').getLogger(__name__)

def _do_list_sites(args, root):
    sites = get_sites_folder(root)

    for site in sites.values():
        print(site.id)

def main():
    with run_as_onboarding_main(_do_list_sites, use_transaction_runner=False) as parser:
        parser.description = 'List all sites'

if __name__ == '__main__':
    main()
