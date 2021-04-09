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

class InvalidPendoAccount(Exception):
    """
    Raised by an IPendoClient if it can't push data to the provided account.
    """

class IPendoClient(interface.Interface):
    """
    Typically adapted from an ILMSSite though can also be loaded as a utility.
    In general you should use clients adapted from an ILMSSite. those clients will
    a) ensure we actually want to allow syncing for a site in a given environment,
    and b) restrict account level operations to only the account that maps to that site.

    Using the generic IPendoClient utility is much more powerful/flexible, but puts the onus
    on the user to make sure they are doing what they want.
    """
    def set_metadata_for_accounts(metadata):
        """
        Set the provided metadata. metadata is a mapping from an IPendoAccount
        or object adaptable to IPendoAccount to a dictionary of pendo fields to values.
        """
