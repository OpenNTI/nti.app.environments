import uuid

from zope import interface

from zope.container.contained import Contained

from zope.container.btree import BTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.property.property import alias

from nti.traversal.traversal import find_interface

from nti.wref.interfaces import IWeakRef

from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import ILMSSitesContainer

from .interfaces import ICheckoutSession
from .interfaces import ICheckoutSessionStorage

@interface.implementer(ICheckoutSession)
class CheckoutSession(PersistentCreatedModDateTrackingObject, Contained):

    createDirectFieldProperties(ICheckoutSession, omit=('customer', 'site'))

    __name__ = alias('id')

    def __init__(self):
        self.id = uuid.uuid4().hex

    def _get_customer(self):
        customer = self._customer_ref() if self._customer_ref else None
        if find_interface(customer, ICustomersContainer, strict=False) is None:
            return None
        return customer

    def _set_customer(self, customer):
        self._customer_ref = IWeakRef(customer) if customer else None

    customer = property(_get_customer, _set_customer)

    def _get_site(self):
        site = self._site_ref() if self._site_ref else None
        if find_interface(site, ILMSSitesContainer, strict=False) is None:
            return None
        return site

    def _set_site(self, site):
        self._site_ref = IWeakRef(site) if site else None

    site = property(_get_site, _set_site)

@interface.implementer(ICheckoutSessionStorage)
class CheckoutSessionStorage(BTreeContainer):

    def track_session(self, customer, site):
        """
        Start tracking a checkout session for the provided customer and site.
        returns ICheckoutSession
        """
        session = CheckoutSession()
        session.customer = customer
        session.site = site
        self[session.id] = session
        return session
        

    def find_session(self, id):
        """
        Return the ICheckoutSession with the given id or None if
        no session with the id exists.
        """
        return self.get(id)


STRIPE_CHECKOUT_SESSIONS_KEY = 'stripe_subscription_checkout_sessions'

def _sessions_from_root(root):
    return root[STRIPE_CHECKOUT_SESSIONS_KEY]
