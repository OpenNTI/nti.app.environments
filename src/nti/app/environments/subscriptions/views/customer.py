from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope.cachedescriptors.property import Lazy

from nti.externalization.interfaces import LocatedExternalDict

from nti.app.environments.models.utils import get_onboarding_root

from nti.app.environments.stripe.interfaces import IStripeCustomer

from nti.app.environments.views.base import BaseView

from nti.app.environments.stripe.interfaces import IStripeBillingPortal
from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeCheckout

from nti.app.environments.subscriptions.interfaces import ICheckoutSessionStorage

from ..auth import ACT_STRIPE_LINK_CUSTOMER
from ..auth import ACT_STRIPE_MANAGE_BILLING

logger = __import__('logging').getLogger(__name__)

@view_config(renderer='rest',
             permission=ACT_STRIPE_LINK_CUSTOMER,
             request_method='PUT',
             context=IStripeCustomer)
class ManageStripeCustomerInfoView(BaseView):

    def __call__(self):
        old = self.context.customer_id
        self.context.customer_id = self.body_params['customer_id']
        res = LocatedExternalDict()
        res.__parent__ = self.context.__parent__
        res.__name__ = self.context.__name__
        res['customer_id'] = self.context.customer_id
        logger.info('%s changed %s stripe customer id from %s to %s',
                    self.request.authenticated_userid,
                    self.context.__parent__.email,
                    old,
                    self.context.customer_id)
        return res

@view_config(renderer='templates/trigger_checkout.pt',
             permission=ACT_STRIPE_MANAGE_BILLING,
             request_method='GET',
             name='manage_billing',
             context=IStripeCustomer)
class ManageBillingView(BaseView):

    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)

    def __call__(self):

        key = component.getUtility(IStripeKey)
        portal = IStripeBillingPortal(key)

        return_url = self.request.params.get('return')
        if not return_url:
            return_url = self.request.resource_url(self.context.__parent__, '@@details')

        owner = self.context.__parent__

        checkout = IStripeCheckout(self.stripe_key)

        checkout_storage = ICheckoutSessionStorage(get_onboarding_root(self.request))
        checkout_item = checkout_storage.track_session(owner, None)
        self.request.environ['nti.request_had_transaction_side_effects'] = True

        session = checkout.generate_setup_session(return_url,
                                                  return_url,
                                                  client_reference_id=checkout_item.id,
                                                  customer=self.context
        )
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'stripe_checkout_session': session.id
        }


