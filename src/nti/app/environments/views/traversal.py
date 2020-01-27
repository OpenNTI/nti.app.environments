from pyramid.interfaces import IRequest

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import component
from zope import interface

from zope.container.contained import Contained

from zope.cachedescriptors.property import Lazy

from zope.traversing.interfaces import IPathAdapter

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_CREATE

from nti.app.environments.models.interfaces import ICustomer

from nti.app.environments.interfaces import ISitesCollection


@interface.implementer(ISitesCollection)
class SitesCollection(Contained):

    __name__ = 'sites'

    def __init__(self, context):
        self.context = context
        self.__parent__ = context

    @Lazy
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, self.__parent__.email, (ACT_CREATE, ACT_READ))]


@interface.implementer(IPathAdapter)
@interface.implementer(ISitesCollection)
@component.adapter(ICustomer, IRequest)
def CustomerSitesPathAdapter(context, unused_request):
    return SitesCollection(context)
