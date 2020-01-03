from zope import interface

class IOTPGenerator(interface.Interface):
    """
    An object capable of generating a secure one-time user passphrase
    """

    def generate_passphrase():
        """
        Returns an appropriate passphrase or one time challenge
        """


class ISiteCreatedNotifier(interface.Interface):
    """
    An object capable of sending notification to target user when a site is created.
    """
    def notify():
        """
        Send notification via email, SMS etc.
        """
