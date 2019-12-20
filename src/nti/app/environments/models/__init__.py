from zope import interface

from zope.container.folder import Folder

from .interfaces import IOnboardingRoot

from .customers import CustomersFolder
from .sites import SitesFolder

_ROOT_KEY = 'onboarding_root'
CUSTOMERS = 'customers'
SITES = 'sites'


@interface.implementer(IOnboardingRoot)
class OnboardingRoot(Folder):
    __parent__ = None
    __name__ = None


def _install_customers(onboarding_root):
    if CUSTOMERS not in onboarding_root:
        customers = CustomersFolder()
        customers.__name__ = CUSTOMERS
        onboarding_root[CUSTOMERS] = customers
    return onboarding_root[CUSTOMERS]


def _install_sites(onboarding_root):
    if SITES not in onboarding_root:
        sites = SitesFolder()
        sites.__name__ = SITES
        onboarding_root[SITES] = sites
    return onboarding_root[SITES]


def _install_root(zodb_root, key=_ROOT_KEY):
    root = OnboardingRoot()

    _install_customers(root)
    _install_sites(root)

    zodb_root[key] = root
    return root


def appmaker(zodb_root):
    if _ROOT_KEY not in zodb_root:
        _install_root(zodb_root, key=_ROOT_KEY)
    return zodb_root[_ROOT_KEY]
