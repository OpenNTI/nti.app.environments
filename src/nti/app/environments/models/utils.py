from pyramid.threadlocal import get_current_request

from nti.app.environments.models import CUSTOMERS
from nti.app.environments.models import SITES
from nti.app.environments.models import HOSTS
from nti.app.environments.models import IOnboardingRoot
from nti.app.environments.models.interfaces import IDedicatedEnvironment


def get_onboarding_root(request=None):
    request = request or get_current_request()
    return IOnboardingRoot(request)


def _get_root_child(key, onboarding_root=None, request=None):
    if onboarding_root is None:
        onboarding_root = get_onboarding_root(request=request)
    return onboarding_root[key]


def get_customers_folder(onboarding_root=None, request=None):
    return _get_root_child(CUSTOMERS, onboarding_root=onboarding_root, request=request)


def get_sites_folder(onboarding_root=None, request=None):
    return _get_root_child(SITES, onboarding_root=onboarding_root, request=request)


def get_hosts_folder(onboarding_root=None, request=None):
    return _get_root_child(HOSTS, onboarding_root=onboarding_root, request=request)


def maybe_recompute_host_load_with_site(site, exclusive=False):
    if IDedicatedEnvironment.providedBy(site.environment):
        host = site.environment.host
        if exclusive:
            host.recompute_current_load(exclusive_site=site)
        else:
            host.recompute_current_load()


def recompute_host_loads_with_sites(sites=None):
    data = {}
    sites = sites or get_sites_folder().values()
    for site in sites or ():
        if not IDedicatedEnvironment.providedBy(site.environment):
            continue

        host = site.environment.host
        data[host] = data[host] + 1 if host in data else 1

    for host, current_load in data.items():
        host.set_current_load(current_load=current_load)
