from zope import interface

from zope.securitypolicy.interfaces import IPrincipalRoleManager


class IOTPGenerator(interface.Interface):
    """
    An object capable of generating a secure one-time user passphrase
    """

    def generate_passphrase():
        """
        Returns an appropriate passphrase or one time challenge
        """

class IOnboardingServer(interface.Interface):
    pass


class IOnboardingRootPrincipalRoleManager(IPrincipalRoleManager):
    pass
