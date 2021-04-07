from zope import interface

from nti.schema.field import ValidTextLine
from nti.schema.field import HTTPURL


class IPendoAccount(interface.Interface):
    """
    A representation of an Account in pendo. Typically
    we map our sites to these.
    """

    account_id = ValidTextLine(title='The identifier of the account in pendo')

    account_web_url = HTTPURL(title='The url to the account page')

class MissingPendoAccount(Exception):
    """
    An exception raised when account_id has not been assigned a value.
    """

class IPendoClient(interface.Interface):
    def set_metadata_for_accounts(metadata):
        """
        Set the provided metadata. metadata is a mapping from an IPendoAccount
        or object adaptable to IPendoAccount to a dictionary of pendo fields to values.
        """

    def send_track_event(event, account, visitor, timestamp=None, properties=None, context={}):
        """
        Manually track an event for the provided visitor
        
        https://support.pendo.io/hc/en-us/articles/360032294291-Track-Events-Configuration
        """
