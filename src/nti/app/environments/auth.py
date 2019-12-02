from zope import interface

from pyramid.interfaces import IAuthenticationPolicy

from pyramid.authentication import AuthTktAuthenticationPolicy as _AuthTktAuthenticationPolicy

from zope.securitypolicy.interfaces import Allow

from zope.securitypolicy.principalrole import principalRoleManager


ACT_ADMIN = 'nti.actions.admin'
ADMIN_ROLE = 'nti.roles.admin'


@interface.implementer(IAuthenticationPolicy)
class AuthenticationPolicy(_AuthTktAuthenticationPolicy):

    def effective_principals(self, request):
        result = _AuthTktAuthenticationPolicy.effective_principals(self, request)
        userid = self.unauthenticated_userid(request)
        if userid:
            roles = principalRoleManager.getRolesForPrincipal(userid)
            for role, access in roles or ():
                if role == ADMIN_ROLE and access == Allow:
                    result.append(ADMIN_ROLE)
        return result
