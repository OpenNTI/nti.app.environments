from pyramid.interfaces import IRootFactory

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import component
from zope.cachedescriptors.property import Lazy

from nti.property.property import LazyOnClass

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import ACT_READ

from .models.interfaces import IOnboardingRoot


class AdminResource(object):
    """
    See https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/hybrid.html#hybrid-chapter
    https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/resources.html#overriding-resource-url-generation
    """
    def __init__(self, request):
        self.request = request
        self._data = {'dashboards': DashboardsResource(self)}

    @Lazy
    def root(self):
        return IOnboardingRoot(self.request)

    def __getitem__(self, name):
        res = self.root.get(name)
        return res if res is not None else self._data.get(name)


class DashboardsResource(object):

    __name__ = 'dashboards'
    __parent__ = None

    def __init__(self, parent):
        self.__parent__ = parent

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, ACT_READ)]


def admin_root_factory(request):
    return AdminResource(request)
