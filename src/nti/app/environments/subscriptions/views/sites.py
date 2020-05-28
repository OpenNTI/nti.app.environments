import datetime

from zope import component

from zope.cachedescriptors.property import Lazy

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.externalization.interfaces import LocatedExternalDict

from nti.app.environments.auth import ACT_READ

from nti.app.environments.common import formatDateToLocal

from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_SUBSCRIPTION
from nti.app.environments.subscriptions.auth import ACT_STRIPE_LINK_SUBSCRIPTION

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.utils import get_onboarding_root

from nti.app.environments.views.base import BaseView

from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeCheckout
from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.interfaces import IStripeSubscriptionBilling

from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_BILLING
from nti.app.environments.subscriptions.interfaces import ICheckoutSessionStorage

@view_config(renderer='rest',
             permission=ACT_STRIPE_LINK_SUBSCRIPTION,
             request_method='PUT',
             context=IStripeSubscription)
class ManageStripSubscriptionInfoView(BaseView):

    def __call__(self):
        self.context.id = self.body_params['subscription_id']
        res = LocatedExternalDict()
        res.__parent__ = self.context.__parent__
        res.__name__ = self.context.__name__
        res['subscription_id'] = self.context.id
        return res

@view_config(renderer='templates/manage_subscription.pt',
             permission=ACT_STRIPE_MANAGE_SUBSCRIPTION,
             request_method='GET',
             context=ILMSSite,
             name='manage_subscription')
class ManageSubscriptionPage(BaseView):

    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)

    def trial_data(self):
        if not ITrialLicense.providedBy(self.context.license):
            return None

        license = self.context.license
        now = datetime.datetime.utcnow()
        delta = license.end_date - now

        return {'remaining_days': max(delta.days, 0),
                'ended': license.end_date < now}

    def format_date(self, datetime):
        return formatDateToLocal(datetime, _format='%B %-d, %Y')

    def format_currency(self, amount):
        # TODO assuming usd here. Also not correctly
        # dealing with other i18n issues like seperators
        return "${:0,.2f}".format(round(amount/100,2))
    
    @Lazy
    def license(self):
        return self.context.license

    @Lazy
    def upcoming_invoice(self):
        subscription = IStripeSubscription(self.context, None)
        if not subscription.id:
            return None
        billing = IStripeSubscriptionBilling(self.stripe_key)
        return billing.get_upcoming_invoice(subscription)
    
    def plan_classes(self, plan):
        classes = ['plan']

        if plan == self.license.license_name:
            classes.append('selected')
        elif not ITrialLicense.providedBy(self.license):
            classes.append('disabled')

        return ' '.join(classes)

    def allows_plan_updates(self):
        return ITrialLicense.providedBy(self.license)

    def plan_options(self):
        return {
            'products': ['trial', 'starter', 'growth', 'enterprise'],
            'product_details': {
                'trial': {
                    'cost': 0
                },
                'starter': {
                    'seat_options': [x+1 for x in range(0, 5)],
                    'plans': [{
                        'plan_id': 'plan_H0mGeIfpAIA8EY',
                        'frequency': 'yearly',
                        'cost': 99
                    },{
                        'plan_id': 'plan_H0mGeIfpAIA8EY',
                        'frequency': 'monthly',
                        'cost': 119
                    }]
                },
                'growth': {
                    'seat_options': [x+1 for x in range(0, 10)],
                    'plans': [{
                        'plan_id': 'plan_H0mFrbr2v0gKKh',
                        'frequency': 'yearly',
                        'cost': 199
                    },{
                        'plan_id': 'plan_H0mF4xaJYoOvpz',
                        'frequency': 'monthly',
                        'cost': 239
                    }]
                },
                'enterprise': {
                    'cost': 299
                },
            }
            
        }
    
    def __call__(self):
        if self.stripe_key is None:
            raise hexc.HTTPNotFound()

        billing_link = None
        sc = IStripeCustomer(self.context.owner, None)
        if sc and self.request.has_permission(ACT_STRIPE_MANAGE_BILLING, sc):
            billing_link = self.request.resource_url(sc, '@@manage_billing')
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'submit': self.request.resource_url(self.context, '@@manage_subscription'),
            'username': self.request.authenticated_userid,
            'trial': self.trial_data(),
            'license': self.context.license,
            'upcoming_invoice': self.upcoming_invoice,
            'manage_billing': billing_link if not ITrialLicense.providedBy(self.context.license) else None,
            'plans': self.plan_options()
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

        # We only let you subscribe online if you are currently in a trial license
        # with no associated subscription.
        #
        # User's should be able to get this far unless they are trying to let themselves
        # in the backdoor. This acts as a safety check.
        if not ITrialLicense.providedBy(self.context.license):
            logger.warn('Can only subscribe online if you are a trial license')
            raise hexc.HTTPBadRequest()

        subscription = IStripeSubscription(self.context)
        if subscription.id:
            logger.warn('Site already has a subscription %s', subscription.id)
            raise hexc.HTTPBadRequest()

        class Plan(object):
            plan = None
            quantity = 0

            def __init__(self, plan, quantity):
                self.plan = plan
                self.quantity = quantity

        plan = Plan(self.request.params.get('plan'),
                    int(self.request.params.get('seats')))

        # TODO validate the plan here. Is it a valid plan to transition
        # to. Is the number of seats appropriate?
        # lookup by plan_id, validate min and max seats against product
        

        owner = self.context.owner
        assert owner

        checkout_storage = ICheckoutSessionStorage(get_onboarding_root(self.request))
        checkout_item = checkout_storage.track_session(owner, self.context)
        
        stripe_customer = component.queryAdapter(owner, IStripeCustomer)

        checkout = IStripeCheckout(self.stripe_key)
        session = checkout.generate_subscription_session([plan],
                                                         self.request.url,
                                                         self.request.url,
                                                         client_reference_id=checkout_item.id,
                                                         customer=stripe_customer,
                                                         customer_email=owner.email if stripe_customer is None else None,
                                                         metadata={'SiteId': self.context.id}
        )
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'stripe_checkout_session': session.id
        }


