from zope import interface

from nti.schema.fieldproperty import createDirectFieldProperties

import stripe

from .interfaces import IStripeCheckoutSession
from .interfaces import IStripeCheckout

@interface.implementer(IStripeCheckout)
class StripeCheckout(object):
    
    def __init__(self, keys):
        self._keys = keys

    def generate_subscription_session(self,
                                      subscription_items,
                                      cancel_url,
                                      success_url,
                                      customer=None,
                                      customer_email=None,
                                      metadata=None,
                                      client_reference_id=None):

        items = [{'plan': item.plan, 'quantity': item.quantity} for item in subscription_items]
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='subscription',
            subscription_data={
                'items': items,
                'metadata': metadata
            },
            customer=customer.customer_id if customer else None,
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=client_reference_id,
            api_key=self._keys.secret_key
        )
        return session

    def generate_setup_session(self,
                               cancel_url,
                               success_url,
                               customer=None,
                               **kwargs):
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            mode='setup',
            customer=customer.customer_id if customer else None,
            success_url=success_url,
            cancel_url=cancel_url,
            api_key=self._keys.secret_key,
            **kwargs
        )
        return session
