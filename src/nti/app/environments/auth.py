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


def is_admin(userid):
    roles = principalRoleManager.getRolesForPrincipal(userid)
    for role, access in roles or ():
        if role == ADMIN_ROLE and access == Allow:
            return True
    return False


@interface.implementer(IAuthenticationPolicy)
class AuthenticationPolicy(_AuthTktAuthenticationPolicy):

    def effective_principals(self, request):
        result = _AuthTktAuthenticationPolicy.effective_principals(self, request)
        userid = self.unauthenticated_userid(request)
        if userid and is_admin(userid):
            result.append(ADMIN_ROLE)
        return result
