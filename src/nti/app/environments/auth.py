from zope import interface

from pyramid.interfaces import IAuthenticationPolicy

from pyramid.authentication import AuthTktAuthenticationPolicy as _AuthTktAuthenticationPolicy

from zope.securitypolicy.interfaces import Allow

from zope.securitypolicy.principalrole import principalRoleManager


ACT_READ = 'zope.View'
ACT_CREATE = 'nti.actions.create'
ACT_UPDATE = 'nti.actions.update'
ACT_DELETE = 'nti.actions.delete'
ACT_ADMIN = 'nti.actions.admin'
ACT_EDIT_SITE_LICENSE = 'nti.app.environments.actions.edit_site_license'
ACT_EDIT_SITE_ENVIRONMENT = 'nti.app.environments.actions.edit_site_environment'

ADMIN_ROLE = 'role:nti.roles.admin'
ACCOUNT_MANAGEMENT_ROLE = 'role:nti.roles.account-management'


def is_admin_or_account_manager(userid):
    roles = principalRoleManager.getRolesForPrincipal(userid)
    for role, access in roles or ():
        if role in (ADMIN_ROLE, ACCOUNT_MANAGEMENT_ROLE) and access == Allow:
            return True
    return False


def _registered_roles(userid):
    result = []
    roles = principalRoleManager.getRolesForPrincipal(userid)
    for role, access in roles or ():
        if role in (ADMIN_ROLE, ACCOUNT_MANAGEMENT_ROLE) and access == Allow:
            result.append(role)
    return result


@interface.implementer(IAuthenticationPolicy)
class AuthenticationPolicy(_AuthTktAuthenticationPolicy):

    def effective_principals(self, request):
        result = _AuthTktAuthenticationPolicy.effective_principals(self, request)
        userid = self.unauthenticated_userid(request)
        if userid:
            roles = _registered_roles(userid)
            result.extend(roles)

            # For now we grant all NextThought users account management role.
            if userid.endswith('@nextthought.com'):
                result.append(ACCOUNT_MANAGEMENT_ROLE)
        return result
