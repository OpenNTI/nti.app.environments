from zope import interface

from .interfaces import IStripeKey

from nti.externalization.persistence import NoPickle

from nti.schema.fieldproperty import createDirectFieldProperties

@NoPickle
@interface.implementer(IStripeKey)
class StripeKey(object):

    createDirectFieldProperties(IStripeKey)

    def __init__(self, publishable, secret):
        self.publishable_key = publishable
        self.secret_key = secret
