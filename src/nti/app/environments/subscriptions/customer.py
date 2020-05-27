from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from zope.annotation.interfaces import IAnnotations

from nti.app.environments.models.interfaces import ICustomer

from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.customer import MinimalStripeCustomer

STRIPE_CUSTOMER_ANNOTATION_KEY = 'stripe_customer'

@component.adapter(ICustomer)
@interface.implementer(IStripeCustomer)
def stripe_customer_factory(customer, create=True):
    result = None
    annotations = IAnnotations(customer)
    try:
        result = annotations[STRIPE_CUSTOMER_ANNOTATION_KEY]
    except KeyError:
        if create:
            result = MinimalStripeCustomer()
            annotations[STRIPE_CUSTOMER_ANNOTATION_KEY] = result
            result.__name__ = STRIPE_CUSTOMER_ANNOTATION_KEY
            result.__parent__ = customer
    return result


