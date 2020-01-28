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
from nti.app.environments.auth import is_admin_or_account_manager

from nti.app.environments.models.interfaces import ICustomer

from nti.app.environments.models.utils import does_customer_have_sites

from nti.app.environments.interfaces import ISitesCollection


@interface.implementer(ISitesCollection)
class SitesCollection(Contained):

    __name__ = 'sites'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    @Lazy
    def __acl__(self):
        result= [(Allow, ADMIN_ROLE, ALL_PERMISSIONS)]

        if is_admin_or_account_manager(self.__parent__.email, self.request) \
            or not does_customer_have_sites(self.__parent__):
            result.append((Allow, self.__parent__.email, (ACT_CREATE, ACT_READ)))
        else:
            result.append((Allow, self.__parent__.email, ACT_READ))
        return result


@interface.implementer(IPathAdapter)
@interface.implementer(ISitesCollection)
@component.adapter(ICustomer, IRequest)
def CustomerSitesPathAdapter(context, request):
    return SitesCollection(context, request)
