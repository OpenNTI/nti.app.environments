from persistent import Persistent

from zope import interface

from zope.location.interfaces import IContained

from nti.externalization.persistence import NoPickle

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.eqhash import EqHash

import stripe

from .interfaces import IStripeCustomer
from .interfaces import IStripeSubscription
from .interfaces import IStripeSubscriptionBilling
from .interfaces import IStripePayments

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

    def update_subscription_payment_method(self, subscription, payment_method):
        resp = stripe.Subscription.modify(
            getattr(subscription, 'id', subscription),
            default_payment_method=getattr(payment_method, 'id', payment_method),
            api_key=self._keys.secret_key
        )
        return resp

    def update_customer_default_payment_method(self, customer, payment_method):
        resp = stripe.Customer.modify(
            getattr(customer, 'customer_id', customer),
            invoice_settings={
                'default_payment_method': getattr(payment_method, 'id', payment_method)
            },
            api_key=self._keys.secret_key
        )
        return resp

@interface.implementer(IStripePayments)
class StripePayments(object):

    def __init__(self, keys):
        self._keys = keys

    def get_setup_intent(self, intent):
        resp = stripe.SetupIntent.retrieve(getattr(intent, 'id', intent),
                                           api_key=self._keys.secret_key)
        return resp
