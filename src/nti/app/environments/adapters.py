from zope import component
from zope import interface

from ZODB.interfaces import IBroken

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.interfaces import IOnboardingRootPrincipalRoleManager

from nti.externalization.interfaces import IExternalObject

logger = __import__('logging').getLogger(__name__)

@interface.implementer(IOnboardingRootPrincipalRoleManager)
class OnboardingRootPrincipalRoleManager(AnnotationPrincipalRoleManager):
    pass


@interface.implementer(IOnboardingRootPrincipalRoleManager)
@component.adapter(IOnboardingRoot)
def _principal_role_manager(onboarding_root):
    return OnboardingRootPrincipalRoleManager(onboarding_root)

@component.adapter(IBroken)
@interface.implementer(IExternalObject)
class BrokenExternalObject(object):
    """
    Renders broken object. This is mostly for (legacy) logging purposes, as the general
    NonExternalizableObject support catches these now.

    TODO: Consider removing this. Is the logging worth it? Alternately, should the
    NonExternalizableObject adapter be at the low level externization package or
    up here?
    """

    def __init__(self, broken):
        self.broken = broken

    def toExternalObject(self, **unused_kwargs):
        # Broken objects mean there's been a persistence
        # issue. Ok to log it because since its broken, it won't try to call
        # back to us
        logger.debug("Broken object found %s, %s",
                     type(self.broken), self.broken)
        result = {'Class': 'BrokenObject'}
        return result
