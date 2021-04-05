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

class IPendoClient(interface.Interface):
    def set_metadata_for_accounts(metadata):
        """
        Set the provided metadata. metadata is a mapping from an IPendoAccount
        or object adaptable to IPendoAccount to a dictionary of pendo fields to values.
        """

class MissingPendoAccount(Exception):
    """
    An exception raised when account_id has not been assigned a value.
    """
