from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.traversing.interfaces import IPathAdapter

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeSubscription

@interface.implementer(IPathAdapter)
@component.adapter(ICustomer, IRequest)
def StripeCustomerPathAdapter(context, request):
    return IStripeCustomer(context)

@interface.implementer(IPathAdapter)
@component.adapter(ILMSSite, IRequest)
def StripeSubscriptionPathAdapter(context, request):
    return IStripeSubscription(context)
