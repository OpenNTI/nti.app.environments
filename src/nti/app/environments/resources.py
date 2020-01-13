from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from nti.property.property import LazyOnClass

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import ACT_READ

from .models.interfaces import IOnboardingRoot

class DashboardsResource(object):

    __name__ = 'dashboards'
    __parent__ = None

    def __init__(self, request):
        self.__parent__ = IOnboardingRoot(request)

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, ACT_READ)]


class RolesResource(object):

    __name__ = 'roles'
    __parent__ = None

    def __init__(self, request):
        self.__parent__ = IOnboardingRoot(request)

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS)]
