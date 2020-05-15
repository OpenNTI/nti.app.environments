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
