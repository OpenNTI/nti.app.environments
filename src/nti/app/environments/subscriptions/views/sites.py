import datetime

from zope import component

from zope.cachedescriptors.property import Lazy

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from stripe.error import InvalidRequestError

from nti.externalization.interfaces import LocatedExternalDict

from nti.traversal.traversal import find_interface

from nti.app.environments.auth import ACT_READ

from nti.app.environments.common import formatDateToLocal

from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_SUBSCRIPTION
from nti.app.environments.subscriptions.auth import ACT_STRIPE_LINK_SUBSCRIPTION

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.utils import get_onboarding_root

from nti.app.environments.views.base import BaseView

from nti.app.environments.stripe.interfaces import IStripeKey
from nti.app.environments.stripe.interfaces import IStripeCheckout
from nti.app.environments.stripe.interfaces import IStripeCustomer
from nti.app.environments.stripe.interfaces import IStripeSubscription
from nti.app.environments.stripe.interfaces import IStripeSubscriptionBilling

from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_BILLING
from nti.app.environments.subscriptions.interfaces import ICheckoutSessionStorage
from nti.app.environments.subscriptions.interfaces import IProduct
from nti.app.environments.subscriptions.interfaces import IPrice

logger = __import__('logging').getLogger(__name__)

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


_KNOWN_PRODUCTS = ['trial', 'starter', 'growth', 'enterprise']

@view_config(renderer='templates/manage_subscription.pt',
             permission=ACT_STRIPE_MANAGE_SUBSCRIPTION,
             request_method='GET',
             context=IStripeSubscription,
             name='manage')
class ManageSubscriptionPage(BaseView):

    @Lazy
    def site(self):
        return find_interface(self.context, ILMSSite)

    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)

    def trial_data(self):
        if not ITrialLicense.providedBy(self.site.license):
            return None

        license = self.site.license
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
        return self.site.license

    @Lazy
    def upcoming_invoice(self):
        subscription = IStripeSubscription(self.site, None)
        if not subscription.id:
            return None

        try:
            billing = IStripeSubscriptionBilling(self.stripe_key)
            return billing.get_upcoming_invoice(subscription)
        except InvalidRequestError:
            logger.exception('Unable to fetch upcoming invoice')
            return None
            
    
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
        # Find registered utilities for IProduct. We look for products
        # with specific ids here as a shortcut of completely generalizing the UI
        # If our offerings change we will need to address that, but we don't expect
        # that to be frequent. This is very tightly coupled with the template we render
        # and the configuration of products we expect to be in place.

        #First gather all our products
        products = {pid:component.getUtility(IProduct, name=pid) for pid in _KNOWN_PRODUCTS}
        details = {}

        for pid in _KNOWN_PRODUCTS:
            product = products[pid]
            detail = {}

            if product.max_seats is not None:
                detail['seat_options'] = [x+1 for x in range(product.min_seats, product.max_seats)]

            plans = []

            # We only deal with monthly and yearly prices currently
            for freq in ('yearly', 'monthly'):
                price = getattr(product, freq+'_price', None)
                if price is None:
                    continue

                # UI doesn't show decimals right now (no room given design) but prices are in cents
                # so make sure we only have exact dollars
                assert price.cost % 100 == 0
                plans.append({'plan_id': price.id, 'cost': int(price.cost/100), 'frequency': freq})

            if len(plans) > 1:
                detail['plans'] = plans
            else:
                try:
                    cost = plans[0]['cost']
                except IndexError:
                    cost = 0
                detail['cost'] = cost
            details[pid] = detail
        
        return {
            'products': _KNOWN_PRODUCTS,
            'product_details': details           
        }
    
    def __call__(self):
        if self.stripe_key is None:
            raise hexc.HTTPNotFound()

        if self.site.status != SITE_STATUS_ACTIVE:
            raise hexc.HTTPNotFound()

        billing_link = None
        sc = IStripeCustomer(self.site.owner, None)
        if sc and self.request.has_permission(ACT_STRIPE_MANAGE_BILLING, sc):
            billing_link = self.request.resource_url(sc, '@@manage_billing', query={'return': self.request.url})
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'submit': self.request.url,
            'username': self.request.authenticated_userid,
            'trial': self.trial_data(),
            'license': self.site.license,
            'upcoming_invoice': self.upcoming_invoice,
            'manage_billing': billing_link if not ITrialLicense.providedBy(self.site.license) else None,
            'plans': self.plan_options()
        }

class _Plan(object):
    plan = None
    quantity = None

    def __init__(self, p, q):
        self.plan = p
        self.quantity = q
    
@view_config(renderer='templates/trigger_checkout.pt',
             permission=ACT_STRIPE_MANAGE_SUBSCRIPTION,
             request_method='POST',
             context=IStripeSubscription,
             name='manage')
class SubscriptionCheckout(BaseView):

    @Lazy
    def site(self):
        return find_interface(self.context, ILMSSite)

    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)

    def _as_subscribable_plan(self, price, seats):
        if not price.stripe_plan_id:
            logger.error('Plan %s is not a subscribable stripe plan', price.id)
            raise hexc.HTTPBadRequest('Plan %s is not a subscribable stripe plan' % price.id)
        
        product = price.product
        if product.min_seats is not None and seats < product.min_seats:
            logger.error('Plan requires at least %i seats', product.min_seats)
            raise hexc.HTTPBadRequest('Plan requires at least %i seats' % product.min_seats)

        if product.max_seats is not None and seats > product.max_seats:
            logger.error('Plan allows at most %i seats', product.max_seats)
            raise hexc.HTTPBadRequest('Plan allows at most %i seats' % product.max_seats)
        
        return _Plan(price.stripe_plan_id, seats)
    
    def __call__(self):
        if self.stripe_key is None:
            raise hexc.HTTPNotFound()

        if self.site.status != SITE_STATUS_ACTIVE:
            raise hexc.HTTPNotFound()

        # We only let you subscribe online if you are currently in a trial license
        # with no associated subscription.
        #
        # User's shouldn't be able to get this far unless they are trying to let themselves
        # in the backdoor. This acts as a safety check.
        if not ITrialLicense.providedBy(self.site.license):
            logger.warn('Can only subscribe online if you are a trial license')
            raise hexc.HTTPBadRequest()

        subscription = IStripeSubscription(self.site)
        if subscription.id:
            logger.warn('Site already has a subscription %s', subscription.id)
            raise hexc.HTTPBadRequest()

        plan_id = self.request.params.get('plan', '')
        price = component.queryUtility(IPrice, name=plan_id)
        if not price:
            logger.error('Missing plan with id %s', plan_id)
            raise hexc.HTTPBadRequest()

        seats = int(self.request.params.get('seats', 1))
            

        plan = self._as_subscribable_plan(price, seats)

        owner = self.site.owner
        assert owner

        checkout_storage = ICheckoutSessionStorage(get_onboarding_root(self.request))
        checkout_item = checkout_storage.track_session(owner, self.site)
        
        stripe_customer = component.queryAdapter(owner, IStripeCustomer)

        checkout = IStripeCheckout(self.stripe_key)
        session = checkout.generate_subscription_session([plan],
                                                         self.request.url,
                                                         self.request.url,
                                                         client_reference_id=checkout_item.id,
                                                         customer=stripe_customer,
                                                         customer_email=owner.email if stripe_customer is None else None,
                                                         metadata={'SiteId': self.site.id}
        )
        
        return {
            'stripe_pk': self.stripe_key.publishable_key,
            'stripe_checkout_session': session.id
        }


