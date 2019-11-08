from zope import interface

class IEmailChallenger(interface.Interface):

    def send_challenge_for_email(email):
        pass


class IEmailChallengeCodeGenerator(interface.Interface):

    def generate_challenge_code_for_email(email):
        pass
    
class IEmailChallengeValidator(interface.Interface):

    def validate_challenge(email, code):
        pass
