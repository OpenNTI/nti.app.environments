from pyramid.interfaces import IRequest

from zope import component
from zope import interface

from zope.traversing.interfaces import IPathAdapter

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.stripe.interfaces import IStripeCustomer

@interface.implementer(IPathAdapter)
@component.adapter(ICustomer, IRequest)
def StripeCustomerPathAdapter(context, request):
    return IStripeCustomer(context)
