from zope import interface

from zope.container.folder import Folder

from .interfaces import IOnboardingRoot

ROOT_KEY = 'onboarding'
CUSTOMERS = 'customers'
SITES = 'sites'
HOSTS = 'hosts'

@interface.implementer(IOnboardingRoot)
class OnboardingRoot(Folder):
    __parent__ = None
    __name__ = None
