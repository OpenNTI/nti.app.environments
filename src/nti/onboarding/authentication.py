from pyramid.security import remember as p_remember

from zope import interface

from .interfaces import IEmailChallengeCodeGenerator
from .interfaces import IEmailChallengeValidator

@interface.implementer(IEmailChallengeCodeGenerator)
class HashChallengeCodeGenerator(object):

    def generate_challenge_code_for_email(self, email):
        return str((hash(email) % 1000000))

@interface.implementer(IEmailChallengeValidator)
class HashChallengeValidator(object):

    def validate_challenge(self, email, code):
        return HashChallengeCodeGenerator().generate_challenge_code_for_email(email) == code
        

def remember(request, userid, **kwargs):
    headers = p_remember(request, userid)
    response = request.response
    response.headerlist.extend(headers)
    return response

