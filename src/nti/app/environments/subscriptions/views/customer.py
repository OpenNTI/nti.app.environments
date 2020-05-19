from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.externalization.interfaces import LocatedExternalDict

from nti.app.environments.stripe.interfaces import IStripeCustomer

from nti.app.environments.views.base import BaseView

from nti.app.environments.stripe.interfaces import IStripeBillingPortal
from nti.app.environments.stripe.interfaces import IStripeKey

from ..auth import ACT_STRIPE_LINK_CUSTOMER
from ..auth import ACT_STRIPE_MANAGE_BILLING

@view_config(renderer='rest',
             permission=ACT_STRIPE_LINK_CUSTOMER,
             request_method='PUT',
             context=IStripeCustomer)
class CustomerAuthTokenVerifyView(BaseView):

    def __call__(self):
        self.context.customer_id = self.body_params['customer_id']
        res = LocatedExternalDict()
        res.__parent__ = self.context.__parent__
        res.__name__ = self.context.__name__
        res['customer_id'] = self.context.customer_id
        return res

@view_config(renderer='rest',
             permission=ACT_STRIPE_MANAGE_BILLING,
             request_method='POST',
             name='manage_billing',
             context=IStripeCustomer)
class ManageBillingView(BaseView):

    def __call__(self):
        key = component.getUtility(IStripeKey)
        portal = IStripeBillingPortal(key)

        return_url = self.request.resource_url(self.context.__parent__, '@@details')
        session = portal.generate_session(self.context, return_url)

        return hexc.HTTPSeeOther(location=session.url)


