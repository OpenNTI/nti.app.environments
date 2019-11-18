from zope import interface

from zope.container.folder import Folder

from .interfaces import IOnboardingRoot

from .customers import CustomersFolder

_ROOT_KEY = 'onboarding_root'

@interface.implementer(IOnboardingRoot)
class OnboardingRoot(Folder):
    __parent__ = None
    __name__ = None

def _install_root(zodb_root, key=_ROOT_KEY):
    root = OnboardingRoot()
    root.__name__ = key

    customers = CustomersFolder()
    customers.__name__ = 'customers'
    root['customers'] = customers
    
    zodb_root[key] = root
    return root
    
def appmaker(zodb_root):
    if _ROOT_KEY not in zodb_root:
        _install_root(zodb_root, key=_ROOT_KEY)
    return zodb_root
