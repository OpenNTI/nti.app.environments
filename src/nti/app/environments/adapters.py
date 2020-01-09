from zope import component
from zope import interface

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.interfaces import IOnboardingRootPrincipalRoleManager


@interface.implementer(IOnboardingRootPrincipalRoleManager)
class OnboardingRootPrincipalRoleManager(AnnotationPrincipalRoleManager):
    pass


@interface.implementer(IOnboardingRootPrincipalRoleManager)
@component.adapter(IOnboardingRoot)
def _principal_role_manager(onboarding_root):
    return OnboardingRootPrincipalRoleManager(onboarding_root)
