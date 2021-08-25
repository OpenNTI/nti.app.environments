from pyramid.threadlocal import get_current_request

from nti.traversal.traversal import find_interface

from nti.app.environments.models import CUSTOMERS
from nti.app.environments.models import SITES
from nti.app.environments.models import HOSTS
from nti.app.environments.models import IOnboardingRoot


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


def get_sites_with_owner(owner, sites=None, onboarding_root=None, request=None):
    onboarding_root = onboarding_root or find_interface(owner, IOnboardingRoot, strict=None)
    sites = get_sites_folder(onboarding_root, request).values() if sites is None else sites
    for site in sites:
        if site.owner == owner:
            yield site


def does_customer_have_sites(owner, sites=None, onboarding_root=None, request=None):
    onboarding_root = onboarding_root or find_interface(owner, IOnboardingRoot, strict=None)
    sites = get_sites_with_owner(owner, sites, onboarding_root, request)
    return next(sites, None) is not None
