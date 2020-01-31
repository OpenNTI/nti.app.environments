import datetime

from zope import component

import random

from pyramid.security import forget as p_forget
from pyramid.security import remember as p_remember

from zope import interface

from zope.annotation.interfaces import IAnnotations

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


@interface.implementer(IOTPGenerator)
class DevmodeFixedChallengeOTPGenerator(object):
    """
    A fixed 000000000 passphrase generator, only for devmode.
    """

    def generate_passphrase(self, length=_EMAIL_OTP_PASS_LENGTH):
        return '0' * length


_CHALLENGE_EXPIRATION_TIME = 4*60*60 # 4 hours is pretty long
_CHALLENGE_MAX_ATTEMPTS = 3
_CHALLENGE_ANNOTATION_KEY = 'email_auth_challenge'


def setup_challenge_for_customer(customer):
    """
    Sets up a customer to be challenged. Creates a one time passcode
    with a limited number of attempts and assigns it to the user.

    Returns the the one time use code
    """
    generator = component.getUtility(IOTPGenerator)

    code = generator.generate_passphrase()
    now = datetime.datetime.utcnow()
    attempts = 0

    annotations = IAnnotations(customer)

    # Setting up a new challenge invalidates the old challenge
    # regardless of the attempts
    annotations[_CHALLENGE_ANNOTATION_KEY] = (code, now, attempts)
    return code


def validate_challenge_for_customer(customer, code):
    """
    Validates the provided challenge against the given customer.
    Note that calling this is mutates state. each time we validate
    we bump the number of attempts. Call this only once per challenge
    validation.

    Becareful not to leak information here
    """
    annotations = IAnnotations(customer)

    try:
        expected_code, created, attempts = annotations[_CHALLENGE_ANNOTATION_KEY]
    except KeyError:
        return False

    now = datetime.datetime.utcnow()
    age = now - created

    remaining_attempts = _CHALLENGE_MAX_ATTEMPTS - attempts

    if age.total_seconds() > _CHALLENGE_EXPIRATION_TIME or remaining_attempts < 1:
        del annotations[_CHALLENGE_ANNOTATION_KEY]
        return False

    # we are good on age, and attempts
    if not code or code.lower() != expected_code:
        annotations[_CHALLENGE_ANNOTATION_KEY] = (expected_code, created, attempts+1)
        return False

    del annotations[_CHALLENGE_ANNOTATION_KEY]
    return True


def remember(request, userid, **kwargs):
    headers = p_remember(request, userid)
    response = request.response
    response.headerlist.extend(headers)
    return response

def forget(request):
    headers = p_forget(request)
    response = request.response
    response.headerlist.extend(headers)
    return response
