from zope import component

from pyramid.interfaces import IRootFactory
from pyramid.threadlocal import get_current_request

from nti.app.environments.models import CUSTOMERS
from nti.app.environments.models import SITES
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
