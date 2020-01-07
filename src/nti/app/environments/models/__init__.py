from zope import interface

from zope.app.publication.zopepublication import ZopePublication

from zope.container.folder import Folder

from .interfaces import IOnboardingRoot

from .customers import CustomersFolder
from .sites import SitesFolder

ROOT_KEY = 'onboarding_root'
CUSTOMERS = 'customers'
SITES = 'sites'


@interface.implementer(IOnboardingRoot)
class OnboardingRoot(Folder):
    __parent__ = None
    __name__ = None

def appmaker(zodb_root):
    return zodb_root[ZopePublication.root_name][ROOT_KEY]
