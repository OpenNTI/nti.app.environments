from persistent import Persistent

from zope import interface

from zope.location.interfaces import IContained

from nti.externalization.persistence import NoPickle

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.eqhash import EqHash

import stripe

from .interfaces import IStripeBillingPortalSession
from .interfaces import IStripeBillingPortal
from .interfaces import IStripeCustomer
from .interfaces import IStripeSubscription
from .interfaces import IStripeSubscriptionBilling

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


@EqHash('id')
@interface.implementer(IStripeSubscription, IContained)
class MinimalStripeSubscription(Persistent):

    createDirectFieldProperties(IStripeSubscription)

    def __init__(self, subscription_id=None):
        if subscription_id:
            self.id = subscription_id


@interface.implementer(IStripeSubscriptionBilling)
class StripeSubscriptionBilling(object):

    def __init__(self, keys):
        self._keys = keys

    def get_subscription(self, subscription):
        resp = stripe.Subscription.retrieve(getattr(subscription, 'id', subscription),
                                            api_key=self._keys.secret_key)
        return resp

    def get_upcoming_invoice(self, subscription):
        resp = stripe.Invoice.upcoming(subscription=getattr(subscription, 'id', subscription),
                                       api_key=self._keys.secret_key)
        return resp
