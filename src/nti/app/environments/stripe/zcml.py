from zope import interface

from zope.component.zcml import utility

from zope.configuration.fields import Bool

from zope.schema import TextLine

from nti.common.cypher import get_plaintext

from .client import StripeKey

from .interfaces import IStripeKey
from .interfaces import IWebhookSigningSecret

from .hooks import WebhookSigningSecret

logger = __import__('logging').getLogger(__name__)


class IRegisterStripeKeyDirective(interface.Interface):
    """
    The arguments needed for registering a key
    """

    secret_key = TextLine(title=u"The secret key value. Should not contain spaces",
                           required=True)
   
    publishable_key = TextLine(title=u"The publishable_key key, Should not contain spaces",
                               required=True)


def decode_key(key):
    try:
        return get_plaintext(key)
    except Exception:  # pylint: disable=broad-except
        return key


def registerStripeKey(_context, publishable_key, secret_key):
    """
    Register a stripe key with the given alias
    """
    sk = StripeKey(publishable_key, decode_key(secret_key))
    utility(_context, provides=IStripeKey, component=sk)

class IRegisterStripeWebhookSigningSecretDirective(interface.Interface):
    """
    Arguments needed for registering a new webhook by name
    """
    
    secret = TextLine(title=u"The secret key value. Should not contain spaces",
                          required=True)

    name = TextLine(title=u"The name this secret should be registered with",
                    required=True)


def registerWebhookSecret(_context, secret, name):
    wk = WebhookSigningSecret(decode_key(secret))
    utility(_context, provides=IWebhookSigningSecret, component=wk, name=name)
