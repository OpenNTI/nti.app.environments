from pyramid.interfaces import IRequest

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import component
from zope import interface

from zope.container.contained import Contained

from zope.cachedescriptors.property import Lazy

from zope.location.interfaces import LocationError

from zope.traversing.interfaces import IPathAdapter, ITraversable

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_CREATE
from nti.app.environments.auth import is_admin_or_manager

from nti.app.environments.models.interfaces import ICustomer

from nti.app.environments.models.utils import does_customer_have_sites,\
    get_sites_folder

from nti.app.environments.interfaces import ISitesCollection


@interface.implementer(ISitesCollection)
class SitesCollection(Contained):

    __name__ = 'sites'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    @property
    def owner(self):
        return self.__parent__

    @Lazy
    def __acl__(self):
        result= [(Allow, ADMIN_ROLE, ALL_PERMISSIONS)]

        if is_admin_or_manager(self.owner.email, self.request) \
            or not does_customer_have_sites(self.owner):
            result.append((Allow, self.owner.email, (ACT_CREATE, ACT_READ)))
        else:
            result.append((Allow, self.owner.email, ACT_READ))
        return result

    def __getitem__(self, key):
        sites = get_sites_folder(request=self.request)
        return sites.get(key)


@interface.implementer(ITraversable)
class SitesCollectionTraversable(object):

    def __init__(self, context, request=None):
        self.context = context
        self.request = request

    def traverse(self, key, _):
        sites = get_sites_folder(request=self.request)
        site = sites.get(key)
        if site is None or site.owner != self.context.owner:
            raise LocationError(key)
        return site


@interface.implementer(IPathAdapter)
@interface.implementer(ISitesCollection)
@component.adapter(ICustomer, IRequest)
def CustomerSitesPathAdapter(context, request):
    return SitesCollection(context, request)
