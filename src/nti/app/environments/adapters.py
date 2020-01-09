from zope import component
from zope import interface

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from nti.app.environments.models.interfaces import IOnboardingRoot


@interface.implementer(IPrincipalRoleManager)
@component.adapter(IOnboardingRoot)
def _principal_role_manager(onboarding_root):
    return AnnotationPrincipalRoleManager(onboarding_root)
