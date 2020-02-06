from perfmetrics import set_statsd_client
from perfmetrics import statsd_client_from_uri

from zope import component

from nti.environments.management.interfaces import ISettings


def includeme(unused_config):
    settings = component.getUtility(ISettings)
    if 'statsd' in settings:
        settings = settings['statsd']
    statsd_uri = settings['statsd_uri']
    if statsd_uri:
        # Set up a default statsd client for others to use
        set_statsd_client(statsd_client_from_uri(statsd_uri))
