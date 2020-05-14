#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
import time

import functools

from gevent.pool import Pool

import requests

from zope import component

from nti.app.environments.api.siteinfo import NTClient
from nti.app.environments.api.siteinfo import get_collection
from nti.app.environments.api.siteinfo import get_workspace
from nti.app.environments.api.siteinfo import get_link

from nti.app.environments.api.interfaces import IBearerTokenFactory
from nti.app.environments.api.interfaces import ISiteUsageUpdater

from nti.app.environments.interfaces import ITransactionRunner

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.utils import get_sites_folder

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

PENDO_FIELD_NAMES = (('usagetotalsiteadmincount', 'admin_count'),
                     ('usagetotalinstructorcount', 'instructor_count'),
                     ('usagetotalusercount', 'user_count'),
                     ('usagetotalcoursecount', 'course_count'),
                     ('usagetotalscormpackagecount', 'scorm_package_count'),
                     ('usageusedlicensecount', 'used_seats'))

def _pendo_usage_entry(site):
    # TODO Fill in the account id from somewhere
    entry = {
        'accountId': '',
        'values': {}
    }

    usage = ISiteUsage(site)

    # TODO map usage information to pendo fields
    for pendo, attr in PENDO_FIELD_NAMES:
        entry['values'][pendo] = getattr(usage, attr, None)

    return entry
    
def _push_to_pendo(siteids, root, key, dry_run=False):
    """
    Before pushing to pendo, making sure all custom fields created in pendo.
    https://developers.pendo.io/docs/?python#set-value-for-a-set-of-agent-or-custom-fields

    TODO move this to a utility
    """

    payload = []
    
    sites = get_sites_folder(root)
    for siteid in siteids:
        site = sites[siteid]
        payload_for_site = _pendo_usage_entry(site)
        if payload_for_site:
            payload.append(payload_for_site)

    session = requests.Session()
    session.headers.update({'X-PENDO-INTEGRATION-KEY': key})

    logger.debug('Pendo payload is %s', payload)

    if dry_run:
        logger.warn('Not pushing %i items to pendo due to dry run', len(payload))
        return

    logger.info('Pushing data for %i sites to pendo', len(payload))
    start = time.time()
    resp = session.post('https://app.pendo.io/api/v1/metadata/account/custom/value', json=payload)
    resp.raise_for_status()
    result = resp.json()
    elapsed = time.time() - start
    logger.info('Pushed data to pendo in %s seconds. total=%s, updated=%s, failed=%s',
                elapsed, result['total'], result['updated'], result['failed'])
    
    if result['failed']:
        logger.warn('Errors during pendo push. missing=(%s) errors=(%s)',
                    result.get('missing', ''), result.get('errors', ''))

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
