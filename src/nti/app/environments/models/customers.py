from pyramid.security import Allow
from pyramid.security import Deny
from pyramid.security import Everyone
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained

from nti.property.property import LazyOnClass

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.schema import SchemaConfigured

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import OPS_ROLE
from nti.app.environments.auth import ACT_READ

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ISiteAuthToken
from nti.app.environments.models.interfaces import IHubspotContact
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ISiteAuthTokenContainer

from nti.app.environments.subscriptions.auth import ACT_STRIPE_LINK_CUSTOMER
from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_BILLING


@interface.implementer(IHubspotContact)
class HubspotContact(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IHubspotContact)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.hubspotcontact'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(ISiteAuthToken)
class SiteAuthToken(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ISiteAuthToken)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.siteauthtoken'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(ISiteAuthTokenContainer)
class SiteAuthTokenContainer(CaseInsensitiveCheckingLastModifiedBTreeContainer):
    pass


@interface.implementer(ICustomersContainer)
class CustomersFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ACT_STRIPE_LINK_CUSTOMER),
                (Deny, Everyone, ACT_STRIPE_LINK_CUSTOMER),
                (Deny, Everyone, ACT_STRIPE_MANAGE_BILLING),
                (Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, ACT_READ),
                (Allow, OPS_ROLE, ACT_READ)]

    def addCustomer(self, customer):
        self[customer.email] = customer
        return customer

    def getCustomer(self, email):
        return self.get(email)


@interface.implementer(ICustomer)
class PersistentCustomer(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ICustomer)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.customer'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    def __acl__(self):
        return [(Allow, self.email, ACT_STRIPE_MANAGE_BILLING)]

        
