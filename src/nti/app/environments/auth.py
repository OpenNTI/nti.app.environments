from pyramid_authstack import AuthenticationStackPolicy

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authentication import BasicAuthAuthenticationPolicy

from zope.authentication.interfaces import PrincipalLookupError

from zope.principalregistry.principalregistry import principalRegistry

from zope.securitypolicy.interfaces import Allow, IPrincipalRoleManager

from zope.securitypolicy.principalrole import principalRoleManager
from nti.app.environments.models.interfaces import IOnboardingRoot


ACT_READ = 'zope.View'
ACT_LIST = 'nti.actions.list'
ACT_CREATE = 'nti.actions.create'
ACT_UPDATE = 'nti.actions.update'
ACT_DELETE = 'nti.actions.delete'
ACT_ADMIN = 'nti.actions.admin'
ACT_AUTOMATED_REPORTS = 'nti.actions.automated-reports'
ACT_EDIT_SITE_LICENSE = 'nti.app.environments.actions.edit_site_license'
ACT_EDIT_SITE_ENVIRONMENT = 'nti.app.environments.actions.edit_site_environment'
ACT_REQUEST_TRIAL_SITE = 'nti.app.environments.actions.request_trial_site'
ACT_SITE_LOGIN = 'nti.app.environments.actions.site_login'
ACT_SITE_JWT_TOKEN = 'nti.app.environments.actions.site_jwt_token'
ACT_VIEW_SITE_USAGE = 'nti.app.environments.actions.view_site_usage'

ADMIN_ROLE = 'role:nti.roles.admin'
ACCOUNT_MANAGEMENT_ROLE = 'role:nti.roles.account-management'
OPS_ROLE = 'role:nti.roles.ops-management'

# Users that can only access to some specific reports view.
AUTOMATED_REPORTS_ROLE = 'role:nti.roles.automated-reports'

ALL_ROLES = (ADMIN_ROLE,
             ACCOUNT_MANAGEMENT_ROLE,
             OPS_ROLE,
             AUTOMATED_REPORTS_ROLE)

def is_admin(userid, request):
    roles = _registered_roles(userid, request)
    for role in roles or ():
        if role in (ADMIN_ROLE,):
            return True
    return False


def is_admin_or_manager(userid, request):
    roles = _registered_roles(userid, request)
    for role in roles or ():
        if role in (ADMIN_ROLE, ACCOUNT_MANAGEMENT_ROLE, OPS_ROLE):
            return True
    return False


def _registered_roles(userid, request):
    for mgr in (principalRoleManager, IPrincipalRoleManager(IOnboardingRoot(request))):
        roles = mgr.getRolesForPrincipal(userid)
        for role, access in roles or ():
            if role in ALL_ROLES and access == Allow:
                yield role


def check_credentials(username, password, request):
    try:
        principal = principalRegistry.getPrincipal(username)
    except PrincipalLookupError:
        principal = None

    if principal is None or not principal.validate(password):
        return None

    result = [username]
    roles = _registered_roles(username, request)
    result.extend([x for x in roles])
    return result

def groups_callback(userid, request):
    result = [userid]
    if userid:
        roles = _registered_roles(userid, request)
        result.extend([x for x in roles])
    return result

def create_authentication_policy():
    auth_policy = AuthenticationStackPolicy()
    auth_policy.add_policy('basic', BasicAuthAuthenticationPolicy(check_credentials))
    auth_policy.add_policy('auth_tkt', AuthTktAuthenticationPolicy('foo',
                                                                   hashalg='sha512',
                                                                   callback=groups_callback))
    return auth_policy
