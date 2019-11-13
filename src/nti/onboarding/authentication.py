import random

from pyramid.security import remember as p_remember

from zope import interface

from .interfaces import IOTPGenerator

_Z_BASE_32_ALPHABET = "13456789abcdefghijkmnopqrstuwxyz"
_EMAIL_OTP_PASS_LENGTH = 12

@interface.implementer(IOTPGenerator)
class EmailChallengeOTPGenerator(object):
    """
    A one time passcode generator for use when sending email challenges.

    This implementation takes 12 characters from the z-base-32 alphabet
    which should provide 60 bits of entropy. OTP returned from this generator
    are intended to have a limited lifetime.

    This implementation is based on https://github.com/portier/portier-broker/issues/69
    """
    alphabet = _Z_BASE_32_ALPHABET    

    def generate_passphrase(self, length=_EMAIL_OTP_PASS_LENGTH):
        return ''.join(random.choices(self.alphabet, k=length))
        

def remember(request, userid, **kwargs):
    headers = p_remember(request, userid)
    response = request.response
    response.headerlist.extend(headers)
    return response

