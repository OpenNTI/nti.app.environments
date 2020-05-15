#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
import time

import functools

from gevent.pool import Pool

from zope import component

from nti.app.environments.api.siteinfo import NTClient

from nti.app.environments.api.interfaces import IBearerTokenFactory
from nti.app.environments.api.interfaces import ISiteUsageUpdater

from nti.app.environments.interfaces import ITransactionRunner

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.pendo import make_pendo_client
from nti.app.environments.pendo import PENDO_USAGE_TOTAL_COURSE_COUNT
from nti.app.environments.pendo import PENDO_USAGE_TOTAL_INSTRUCTOR_COUNT
from nti.app.environments.pendo import PENDO_USAGE_TOTAL_SCORM_PACKAGE_COUNT
from nti.app.environments.pendo import PENDO_USAGE_TOTAL_SITE_ADMIN_COUNT
from nti.app.environments.pendo import PENDO_USAGE_TOTAL_USER_COUNT
from nti.app.environments.pendo import PENDO_USAGE_USED_LICENSE_COUNT

from nti.app.environments.utils import run_as_onboarding_main

from nti.externalization import to_external_object

import logging

logger = __import__('logging').getLogger(__name__)

def _do_fetch_site_usage(siteid, username, realname, email, root):
    logger.info('Fetching site usage for %s', siteid)
    site = get_sites_folder(root)[siteid]

    bearer_factory = IBearerTokenFactory(site)
    token = bearer_factory.make_bearer_token(username,
                                             realname=realname,
                                             email=email, ttl=10*60) #ten minutes should be plenty of time
    
    client = NTClient(site, bearer=token)

    updater = component.getUtility(ISiteUsageUpdater)
    usage = updater(site, client)
    return site.id, to_external_object(usage)

def _fetch_site_usage(siteid, username, realname, email, dry_run=False):
    # We're running in our own greenlet so set up our own transaction runner
    runner = component.getUtility(ITransactionRunner)
    try:
        return runner(functools.partial(_do_fetch_site_usage, siteid, username, realname, email),
                      job_name='update usage for %s' % siteid,
                      side_effect_free=dry_run)
    except:
        logger.exception('Failed to update site usage for %s', siteid)
        return siteid, None

PENDO_FIELD_NAMES = ((PENDO_USAGE_TOTAL_SITE_ADMIN_COUNT, 'admin_count'),
                     (PENDO_USAGE_TOTAL_INSTRUCTOR_COUNT, 'instructor_count'),
                     (PENDO_USAGE_TOTAL_USER_COUNT, 'user_count'),
                     (PENDO_USAGE_TOTAL_COURSE_COUNT, 'course_count'),
                     (PENDO_USAGE_TOTAL_SCORM_PACKAGE_COUNT, 'scorm_package_count'),
                     (PENDO_USAGE_USED_LICENSE_COUNT, 'used_seats'))

def _pendo_usage_entry(site):
    usage = ISiteUsage(site)
    return {pendo: getattr(usage, attr, None) for (pendo, attr) in PENDO_FIELD_NAMES}

def _push_to_pendo(siteids, root, key, dry_run=False):
    """
    Push usage information for each site to pendo.
    """
    pendo = make_pendo_client(key)

    payload = {}
    
    sites = get_sites_folder(root)
    for siteid in siteids:
        site = sites[siteid]
        payload_for_site = _pendo_usage_entry(site)
        if payload_for_site:
            payload[site] = payload_for_site

    if dry_run:
        logger.warn('Skipping push to pendo because this is a dry run')
        return

    pendo.set_metadata_for_accounts(payload)

PROMETHEUS_METRIC_NAMES = (('usage_total_site_admin_count', 'admin_count'),
                          ('usage_total_instructor_count', 'instructor_count'),
                          ('usage_total_user_count', 'user_count'),
                          ('usage_total_course_count', 'course_count'),
                          ('usage_total_scorm_package_count', 'scorm_package_count'),
                          ('usage_used_license_count', 'used_seats'))

def _push_to_prometheus(siteids, root, gateway, job_name, dry_run=False):
    from prometheus_client import CollectorRegistry, push_to_gateway, Gauge
    
    registry = CollectorRegistry()

    sites = get_sites_folder(root)
    
    for metric_name, field_name in PROMETHEUS_METRIC_NAMES:
        g = Gauge(metric_name, metric_name,
                  labelnames=['site'],
                  registry=registry)

        for siteid in siteids:
            site = sites[siteid]
            usage = ISiteUsage(site)
            val = getattr(usage, field_name, None)
            if val is not None:
                g.labels(siteid).set(val)

    if dry_run:
        logger.warn('Not pushing %i items to prometheus due to dry run', len(siteids))
        return
    
    logger.info("Pushing usage to prometheus, gauges(metrics): %s, labels(sites) of each gauge: %s.", len(PROMETHEUS_METRIC_NAMES), len(siteids))
    
    start = time.time()
    push_to_gateway(gateway, job=job_name, registry=registry)

    print("Pushed usage to prometheus, elapsed: %s seconds." % (time.time()-start))


def _do_fetch_usage(args, root):
    sites = get_sites_folder(root)
    
    logger.info('Querying usage for %i sites', len(sites))

    # Setup of gevent pool to pull usage for each active site
    pool = Pool(args.pool_size)

    def _call_fetch_site_usage(siteid):
        return _fetch_site_usage(siteid,
                                 args.jwt_username,
                                 args.jwt_name,
                                 args.jwt_email,
                                 root)
    
    results = pool.map(_call_fetch_site_usage, [site.__name__ for site in get_sites_folder(root).values() \
                                                if site.status == SITE_STATUS_ACTIVE])

    updated_sites = {site:result for (site, result) in results if result}
    logger.info('Updated usage for %i sites', len(updated_sites))

    def _push_usage_data(root):
        logger.info('Pushing data for %i updated sites to external sources', len(updated_sites))
        if args.pendo_integration_key:
            _push_to_pendo(updated_sites, root, args.pendo_integration_key, dry_run=args.dry_run)
        if args.push_gateway:
            _push_to_prometheus(updated_sites, root, args.push_gateway, args.job_name, dry_run=args.dry_run)

    runner = component.getUtility(ITransactionRunner)

    # We're just reading data here right now. So make it sideeffect free
    runner(_push_usage_data, side_effect_free=True)
 


def main():
    with run_as_onboarding_main(_do_fetch_usage,
                                use_transaction_runner=False,
                                logging_verbose_level=logging.DEBUG) as parser:
        # TODO better help here
        parser.description = 'Grab Site Usage Information'
        parser.add_argument('-p', '--pool-size',
                            dest='pool_size',
                            type=int,
                            default=5)
        
        parser.add_argument('-u', '--username',
                            dest='jwt_username',
                            required=True)
        parser.add_argument('-e', '--email',
                            dest='jwt_email',
                            required=True)
        parser.add_argument('-n', '--name',
                            dest='jwt_name',
                            required=True)

        parser.add_argument('-d', '--dry-run',
                            action='store_true')

        parser.add_argument('--pendo-integration-key',
                            dest='pendo_integration_key',
                            required=False)

        parser.add_argument('--track',
                            type=str,
                            action='store',
                            dest='push_gateway',
                            required=False,
                            help='The host:port for a prometheus push gateway')
        parser.add_argument('-j', '--job-name',
                            type=str,
                            action='store',
                            dest='job_name',
                            default='onboarding_site_usage',
                            required=False,
                            help='The push_gateway job name to use')        


if __name__ == '__main__':
    main()
