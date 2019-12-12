import string

import re

from z3c.schema.email import isValidMailAddress

from zope import component
from zope import interface

from zope.container.constraints import contains

from zope.container.interfaces import IContainer
from zope.container.interfaces import IContained

from zope.i18n import translate

import zope.i18nmessageid as zope_i18nmessageid

from nti.i18n.locales.interfaces import ICcTLDInformation

from nti.schema.interfaces import InvalidValue

from nti.schema.field import Choice
from nti.schema.field import ValidTextLine
from nti.schema.field import DateTime
from nti.schema.field import Object
from nti.schema.field import ListOrTuple

MessageFactory = zope_i18nmessageid.MessageFactory('nti.app.environments')
_ = MessageFactory

SITE_STATUS = ('new', 'pending', 'active', 'defunct',)

SHARED_ENV_NAMES = ('alpha', 'test', 'prod', 'assoc', 'hrpros')

SITE_STATUS_OPTIONS = ('PENDING', 'ACTIVE', 'INACTIVE',)


class IOnboardingRoot(IContainer):
    """
    The root container for onboarding
    """

#: A sequence of only non-alphanumeric characters
#: or a sequence of only digits and spaces, the underscore, and non-alphanumeric characters
#: (which is basically \W with digits and _ added back
_INVALID_REALNAME_RE = re.compile(r'^\W+$|^[\d\s\W_]+$', re.UNICODE)

def _checkEmailAddress(address):
    """
    Check email address.

    This should catch most invalid but no valid addresses.
    """
    result = False
    if isValidMailAddress(address):
        cctlds = component.getUtility(ICcTLDInformation)
        domain = address.rsplit('.', 1)[-1]
        result = domain.lower() in cctlds.getAvailableTLDs()
    return result


def _isValidEmail(email):
    """
    checks for valid email
    """
    return _checkEmailAddress(email)


def checkEmailAddress(value):
    return bool(value and _isValidEmail(value))


def checkRealname(value):
    """
    Ensure that the realname doesn't consist of just digits/spaces
    or just alphanumeric characters
    """
    if value:
        if _INVALID_REALNAME_RE.match(value):
            raise ValueError('Invalid Realname %s' % (value,), ) # Custom
        # Component parts? TODO: What about 'Jon Smith 3' as 'Jon Smith III'?
        # for x in value.split():
    return True

class InvalidData(InvalidValue):
    """
    Invalid Value
    """

    i18n_message = None

    def __str__(self):
        if self.i18n_message:
            return translate(self.i18n_message)
        return super(InvalidData, self).__str__()

    def doc(self):
        if self.i18n_message:
            return self.i18n_message
        return self.__class__.__doc__

class UsernameContainsIllegalChar(InvalidData):

    def __init__(self, username, allowed_chars):
        self.username = username
        allowed_chars = set(allowed_chars) - set(string.letters + string.digits)
        allowed_chars = u''.join(sorted(allowed_chars))
        self.allowed_chars = allowed_chars
        if not allowed_chars:
            allowed_chars = u'no special characters'
            self.i18n_message = _(
                u'Username contains an illegal character. Only letters, digits, '
                u'and ${allowed_chars} are allowed.',
                mapping={'allowed_chars': allowed_chars}
            )

        super(UsernameContainsIllegalChar, self).__init__(self.i18n_message, 'Username',
                                                          username, value=username)

    def new_instance_restricting_chars(self, restricted_chars):
        allowed_chars = set(self.allowed_chars) - set(restricted_chars)
        return type(self)(self.username, allowed_chars)

# In PY2 string.letters is locale dependent. PY3 removed that in favor of non-locale
# dependent ascii_letters. Is that ok?
_ALLOWED_USERNAME_CHARS = string.ascii_letters + string.digits + '-+.@_'

def checkUsername(username):
    """
    Duplicated from nti.dataserver.entity.py
    """
    username = str(username)
    for c in username:
        if c not in _ALLOWED_USERNAME_CHARS:
            raise UsernameContainsIllegalChar(username, _ALLOWED_USERNAME_CHARS)
    return True

class IHubspotContact(interface.Interface):
    """
    Represents a contact in the HubSpot system
    """

    contact_vid = ValidTextLine(title=u'The hubspot vid for the contact',
                                required=True)


class ICustomer(IContained):
    """
    A representation of a customer.
    """


    email = ValidTextLine(title=u'Email',
                          description=u'The email address for this user',
                          required=True,
                          constraint=checkEmailAddress) #Need to add a constraint here.

    name = ValidTextLine(title=u'Your name',
                         description=u"Your full name",
                         required=False,
                         constraint=checkRealname)

    hubspot_contact = Object(IHubspotContact,
                             title=u'The hubspot contact for this customer',
                             required=False,
                             default=None)

    created = DateTime(title=u'The datetime this customer was created at',
                       required=True)

    last_verified = DateTime(title=u'The datetime this customer was verified via email',
                        required=False)


class ICustomersContainer(IContainer):

    contains(ICustomer)

    def addCustomer(customer):
        """
        Add customer into this container, keyed by email.
        """

    def getCustomer(email):
        """
        Return a customer object or None.
        """


class ISiteLicense(interface.Interface):
    """
    The license governing this site.
    """
    start_date = DateTime(title='The datetime this license starts.',
                          required=True)

    end_date = DateTime(title='The datetime this license ends.',
                        required=True)


class ITrialLicense(ISiteLicense):
    """
    A temporary trial license used for evaluation.
    """

class IEnterpriseLicense(ISiteLicense):
    """
    An enterprise level license.
    """

class IEnvironment(interface.Interface):
    """
    Identifies an environment
    """

class IDedicatedEnvironment(IEnvironment):
    """
    Identifies an environment dedicated to a particular customer.
    """
    pod_id = ValidTextLine(title="The container id for this environment.",
                           required=True)

    host = ValidTextLine(title="The identifier of physical hardware that this environment is running on.",
                         min_length=1,
                         required=True)


class ISharedEnvironment(IEnvironment):
    """
    Identifies an environment which contains sites for multiple customers.
    """
    name = Choice(title="The name for this environment.",
                  values=SHARED_ENV_NAMES,
                  required=True)


class ILMSSite(IContained):

    id = ValidTextLine(title="The identifier of this site.",
                       max_length=40,
                       required=True)

    owner = Object(ICustomer,
                   title=u'The customer that owns this site',
                   required=True)

    owner_username = ValidTextLine(title='The username the owner will have in their environment',
                                   required=True,
                                   constraint=checkUsername)

    dns_names = ListOrTuple(value_type=ValidTextLine(min_length=1),
                            title='DNS names this site is known to be accessible via',
                            required=True,
                            default=tuple())

    license = Object(ISiteLicense,
                     title=u'The license governing access to this site',
                     required=True)

    environment = Object(IEnvironment,
                         title=u'The environment this site is running out of',
                         required=True)

    created = DateTime(title=u'The datetime this site was created at',
                       required=True)

    status = Choice(title=u'The style of the highlight',
                    values=SITE_STATUS_OPTIONS,
                    default='PENDING')


class ILMSSitesContainer(IContainer):

    contains(ILMSSite)

    def addSite(site, siteId=None):
        """
        Add a new site into this container, a site id would be generated for site
        if the given site doens't have an id and siteId is not provided.
        """

    def deleteSite(siteId):
        """
        Remove site with given id.
        """
