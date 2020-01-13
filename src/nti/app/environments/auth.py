from zope import interface

from pyramid.interfaces import IAuthenticationPolicy

from pyramid.authentication import AuthTktAuthenticationPolicy as _AuthTktAuthenticationPolicy

from zope.securitypolicy.interfaces import Allow, IPrincipalRoleManager

from zope.securitypolicy.principalrole import principalRoleManager
from nti.app.environments.models.interfaces import IOnboardingRoot


ACT_READ = 'zope.View'
ACT_CREATE = 'nti.actions.create'
ACT_UPDATE = 'nti.actions.update'
ACT_DELETE = 'nti.actions.delete'
ACT_ADMIN = 'nti.actions.admin'
ACT_EDIT_SITE_LICENSE = 'nti.app.environments.actions.edit_site_license'
ACT_EDIT_SITE_ENVIRONMENT = 'nti.app.environments.actions.edit_site_environment'
ACT_REQUEST_TRIAL_SITE = 'nti.app.environments.actions.request_trial_site'

ADMIN_ROLE = 'role:nti.roles.admin'
ACCOUNT_MANAGEMENT_ROLE = 'role:nti.roles.account-management'


def is_admin(userid, request):
    roles = _registered_roles(userid, request)
    for role in roles or ():
        if role in (ADMIN_ROLE,):
            return True
    return False


def is_admin_or_account_manager(userid, request):
    roles = _registered_roles(userid, request)
    for role in roles or ():
        if role in (ADMIN_ROLE, ACCOUNT_MANAGEMENT_ROLE):
            return True
    return False


def _registered_roles(userid, request):
    for mgr in (principalRoleManager, IPrincipalRoleManager(IOnboardingRoot(request))):
        roles = mgr.getRolesForPrincipal(userid)
        for role, access in roles or ():
            if role in (ADMIN_ROLE, ACCOUNT_MANAGEMENT_ROLE) and access == Allow:
                yield role


@interface.implementer(IAuthenticationPolicy)
class AuthenticationPolicy(_AuthTktAuthenticationPolicy):

    def effective_principals(self, request):
        result = _AuthTktAuthenticationPolicy.effective_principals(self, request)
        userid = self.unauthenticated_userid(request)
        if userid:
            roles = _registered_roles(userid, request)
            result.extend([x for x in roles])
        return result
