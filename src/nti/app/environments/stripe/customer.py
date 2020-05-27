from persistent import Persistent

from zope import interface

from zope.location.interfaces import IContained

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.eqhash import EqHash

from .interfaces import IStripeCustomer

@EqHash('customer_id')
@interface.implementer(IStripeCustomer, IContained)
class MinimalStripeCustomer(Persistent):

    createDirectFieldProperties(IStripeCustomer)

    def __init__(self, customer_id=None):
        if customer_id:
            self.customer_id = customer_id
