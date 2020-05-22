from zope import component

from zope.cachedescriptors.property import Lazy

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.app.environments.auth import ACT_READ
from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_SUBSCRIPTION

from nti.app.environments.models.interfaces import ILMSSite

from nti.app.environments.views.base import BaseView

from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeCheckout
from nti.app.environments.stripe.interfaces import IStripeCustomer

@view_config(renderer='templates/manage_subscription.pt',
             permission=ACT_STRIPE_MANAGE_SUBSCRIPTION,
             request_method='GET',
             context=ILMSSite,
             name='manage_subscription')
class ManageSubscriptionPage(BaseView):

    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)
    
    def __call__(self):
        if self.stripe_key is None:
            raise hexc.HTTPNotFound()
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'submit': self.request.resource_url(self.context, '@@manage_subscription')
        }

@view_config(renderer='templates/trigger_checkout.pt',
             permission=ACT_STRIPE_MANAGE_SUBSCRIPTION,
             request_method='POST',
             context=ILMSSite,
             name='manage_subscription')
class SubscriptionCheckout(BaseView):

    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)
    
    def __call__(self):
        if self.stripe_key is None:
            raise hexc.HTTPNotFound()

        class mockplan(object):
            plan = 'plan_H0mF4xaJYoOvpz'
            quantity = 4

        owner = self.context.owner
        assert owner
        stripe_customer = component.queryAdapter(owner, IStripeCustomer)

        checkout = IStripeCheckout(self.stripe_key)
        session = checkout.generate_subscription_session([mockplan()],
                                                         self.request.url,
                                                         self.request.url,
                                                         customer=stripe_customer,
                                                         customer_email=owner.email if stripe_customer is None else None,
                                                         metadata={'SiteId': self.context.id}
        )
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'stripe_checkout_session': session.id
        }


