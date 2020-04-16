from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.folder import Folder

from nti.app.environments.auth import ADMIN_ROLE

from .interfaces import IOnboardingRoot

ROOT_KEY = 'onboarding'
CUSTOMERS = 'customers'
SITES = 'sites'
HOSTS = 'hosts'

@interface.implementer(IOnboardingRoot)
class OnboardingRoot(Folder):
    __parent__ = None
    __name__ = None

    def __acl__(self):
        result = [(Allow, ADMIN_ROLE, ALL_PERMISSIONS)]
        return result
