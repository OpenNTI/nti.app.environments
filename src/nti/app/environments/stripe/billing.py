from zope import interface

from nti.externalization.persistence import NoPickle

from nti.schema.fieldproperty import createDirectFieldProperties

import stripe

from .interfaces import IStripeBillingPortalSession
from .interfaces import IStripeBillingPortal
from .interfaces import IStripeCustomer

@interface.implementer(IStripeBillingPortal)
class StripeBillingPortal(object):
    
    def __init__(self, keys):
        self._keys = keys

    def generate_session(self, customer, return_url):
        
        resp = stripe.billing_portal.Session.create(
            customer=customer.customer_id,
            return_url=return_url,
            api_key = self._keys.secret_key
        )
        
        return resp
