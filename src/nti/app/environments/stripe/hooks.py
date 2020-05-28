from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.event import notify

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.externalization import new_from_external_object

from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import iface_for_event
from .interfaces import IStripeKey
from .interfaces import IWebhookSigningSecret

import stripe

logger = __import__('logging').getLogger(__name__)

@interface.implementer(IWebhookSigningSecret)
class WebhookSigningSecret(object):

    createDirectFieldProperties(IWebhookSigningSecret)
    
    def __init__(self, secret, tolerance=None):
        self.secret = secret
        if tolerance:
            self.tolerance = tolerance


@view_config(renderer='rest',
             request_method='POST',
             route_name='stripe.hooks')
class StripeHook(object):

    HOOK_NAME = 'default'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @Lazy
    def signing_secret(self):
        return component.getUtility(IWebhookSigningSecret,
                                    name=self.HOOK_NAME)
        
    @Lazy
    def stripe_key(self):
        return component.queryUtility(IStripeKey)
    
    def __call__(self):
        if self.stripe_key is None:
            raise hexc.HTTPNotFound()

        try:
            sig_header = self.request.headers['STRIPE_SIGNATURE']
        except KeyError:
            logger.debug('Received stripe webhook without signature header')
            raise hexc.HTTPBadRequest()

        try:
            event = stripe.Webhook.construct_event(self.request.body,
                                                   sig_header,
                                                   self.signing_secret.secret,
                                                   tolerance=self.signing_secret.tolerance,
                                                   api_key=self.stripe_key.secret_key)
            interface.alsoProvides(event, iface_for_event(event))
        except ValueError:
            logger.debug('Received an invalid payload to stripe webhook')
            raise hexc.HTTPBadRequest()
        except stripe.error.SignatureVerificationError:
            logger.debug('Stripe webhook signature mismatch')
            raise hexc.HTTPBadRequest()

        logger.info('Received a webhook from stripe of type %s', event.type)
        notify(event)            
        logger.info('Processed a webhook from stripe of type %s', event.type)
        
        return hexc.HTTPOk()
