import string

import re

from z3c.schema.email import isValidMailAddress

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.container.constraints import contains

from zope.container.interfaces import IContainer
from zope.container.interfaces import IContained

from zope.i18n import translate

import zope.i18nmessageid as zope_i18nmessageid

from zope.interface.interfaces import IObjectEvent

from nti.i18n.locales.interfaces import ICcTLDInformation

from nti.base.interfaces import ICreatedTime
from nti.base.interfaces import ILastModified

from nti.schema.interfaces import InvalidValue

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import Choice
from nti.schema.field import Object
from nti.schema.field import DateTime
from nti.schema.field import ListOrTuple
from nti.schema.field import ValidTextLine
from nti.schema.field import UniqueIterable
from nti.schema.field import ValidBytesLine

from nti.environments.management.interfaces import IInitializedSiteInfo

MessageFactory = zope_i18nmessageid.MessageFactory('nti.app.environments')
_ = MessageFactory


SHARED_ENV_NAMES = ('alpha', 'test', 'prod', 'assoc', 'hrpros', 'publicstragegies', 'fedramp')


SITE_STATUS_PENDING = 'PENDING'
SITE_STATUS_ACTIVE = 'ACTIVE'
SITE_STATUS_INACTIVE = 'INACTIVE'
SITE_STATUS_UNKNOWN = 'UNKNOWN'
SITE_STATUS_CANCELLED = 'CANCELLED'
SITE_STATUS_ARCHIVED = 'ARCHIVED'
SITE_STATUS_DESTROYED = 'DESTROYED'
# order matters for UI.
SITE_STATUS_OPTIONS = (SITE_STATUS_PENDING,
                       SITE_STATUS_ACTIVE,
                       SITE_STATUS_INACTIVE,
                       SITE_STATUS_CANCELLED,
                       SITE_STATUS_ARCHIVED,
                       SITE_STATUS_DESTROYED,
                       SITE_STATUS_UNKNOWN)


#: Site setup state status options; mirrors ISetupState implementations
SETUP_STATE_STATUS_OPTIONS = (u'pending', u'success', u'failed')

LICENSE_FREQUENCY_MONTHLY = 'monthly'
LICENSE_FREQUENCY_YEARLY = 'yearly'
LICENSE_FREQUENCY_OPTIONS = (LICENSE_FREQUENCY_MONTHLY,
                             LICENSE_FREQUENCY_YEARLY)


class IOnboardingRoot(IContainer, IAttributeAnnotatable):
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


class InvalidSiteError(ValueError):
    pass


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
                         required=True,
                         min_length=1,
                         constraint=checkRealname)

    phone = ValidTextLine(title=u'Phone Number',
                          required=False)

    hubspot_contact = Object(IHubspotContact,
                             title=u'The hubspot contact for this customer',
                             required=False,
                             default=None)

    last_verified = DateTime(title=u'The datetime this customer was verified via email',
                             required=False)

    organization = ValidTextLine(title="The organization name this customer belongs to",
                                 min_length=1,
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


class ISiteAuthToken(ICreatedTime, IContained):
    """
    An authentication token for a particular site. Used in the "setup password"
    flow to validate a user and allow them to acces their site.
    """

    token = ValidBytesLine(title=u"The token value",
                           required=True)


class ISiteAuthTokenContainer(IContainer):
    """
    A container mapping a site_id to a possible :class:`ISiteAuthToken` for a
    user.
    """

    contains(ISiteAuthToken)


class IHost(IContained):

    id = ValidTextLine(title="The id of this host",
                       min_length=1,
                       required=False)

    host_name = ValidTextLine(title="The identifier of physical hardware",
                              min_length=1,
                              required=True)

    capacity = Int(title="The total number of sites this host machine supports.",
                   min=1,
                   required=True)

    current_load = Int(title="The total sites load on this host machine.",
                       required=True)
    current_load.setTaggedValue('_ext_excluded_out', True)


class IHostsContainer(IContainer):

    contains(IHost)

    def addHost(host):
        """
        Add a Host into this container.
        """

    def getHost(host_id):
        """
        Return a host by given host_id.
        """

    def deleteHost(host):
        """
        Remove a given host.
        """

class ISiteLicenseFactory(interface.Interface):
    """
    A callable factory producing an ISiteLicense
    """

class ISiteLicense(interface.Interface):
    """
    The license governing this site.
    """
    license_name = ValidTextLine(title="The license descriptive name",
                                 required=True)

    start_date = DateTime(title='The datetime this license starts.',
                          required=True)

    end_date = DateTime(title='The datetime this license ends.',
                        required=True)

class IRestrictedScorm(interface.Interface):

    max_scorm_packages = Int(title="The number of scorm packages we allow.",
                             required=True,
                             readonly=True, #Right now this is readonly, although that could change in the future
                             min=0)

class ITrialLicense(IRestrictedScorm, ISiteLicense):
    """
    A temporary trial license used for evaluation.
    """


class IEnterpriseLicense(ISiteLicense):
    """
    An enterprise level license.
    """

class IRestrictedLicense(ISiteLicense):

    frequency = Choice(title=u'The frequency',
                       values=LICENSE_FREQUENCY_OPTIONS,
                       required=True)

    seats = Int(title="The number of licensed seats allowed.",
                description="These seats may be used for site admins, or instructors. A value of None indicates no limit",
                required=True,
                min=1)

    additional_instructor_seats = Int(title="The number of instructor add-on seats allowed.",
                                      description="These seats may only be used for instructors. A value of None indicates no additional instructor seats.",
                                      required=False,
                                      min=1)


class IStarterLicense(IRestrictedScorm, IRestrictedLicense):
    """
    A starter level license.
    """


class IGrowthLicense(IRestrictedScorm, IRestrictedLicense):
    """
    A growth level license.
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

    host = Object(IHost,
                  title="The identifier of physical hardware that this environment is running on.",
                  required=True)

    load_factor = Int(title="The load factor.",
                      default=1,
                      min=0,
                      required=True)


class ISharedEnvironment(IEnvironment):
    """
    Identifies an environment which contains sites for multiple customers.
    """
    name = Choice(title="The name for this environment.",
                  values=SHARED_ENV_NAMES,
                  required=True)


class ISetupState(IContained):
    """
    Identifies a site setup state.
    """

    state_name = ValidTextLine(title="The setup state descriptive name",
                               required=True)

    # Right now we track this for all states. We may only
    # need it for pending?
    task_state = Object(interface.Interface,
                        title='The task serialization information')
    task_state.setTaggedValue('_ext_excluded_out', True)

    start_time = DateTime(title=u'The datetime this setup state was created',
                          required=False)

    end_time = DateTime(title=u'The datetime the site transitioned to a finished state',
                        required=False)


class ISetupStatePending(ISetupState):
    """
    A site that is in the process of being setup
    """


class ISetupStateSuccess(ISetupState):
    """
    A site that has successfully gone through the setup process
    """

    site_info = Object(IInitializedSiteInfo,
                       title='Information about the site that was succesfull created')
    site_info.setTaggedValue('_ext_excluded_out', True)

    invite_accepted_date = DateTime(title=u'The datetime the inital invite was accepted',
                                    required=False)

    invitation_active = Bool(title="If the admin invitation code is still active",
                                description="Invitation code may be deleted or expired on platform.",
                                default=True,
                                required=False)


class ISetupStateFailure(ISetupState):
    """
    A site that failed setup
    """

    exception = interface.Attribute('The exception resulting in the failure')
    exception.setTaggedValue('_ext_excluded_out', True)


class ILMSSite(IContained, IAttributeAnnotatable):

    id = ValidTextLine(title="The identifier of this site.",
                       max_length=40,
                       required=False)

    ds_site_id = ValidTextLine(title="The dataserver site name/id.",
                               required=False)

    owner = Object(ICustomer,
                   title=u'The customer that owns this site',
                   required=False)

    dns_names = UniqueIterable(value_type=ValidTextLine(min_length=1),
                               title='DNS names this site is known to be accessible via',
                               required=True,
                               min_length=1)

    license = Object(ISiteLicense,
                     title=u'The license governing access to this site',
                     required=True)

    environment = Object(IEnvironment,
                         title=u'The environment this site is running out of',
                         required=False)

    status = Choice(title=u'The LMS site status',
                    description=u"""The site status is used by internal site managers to
                    define the current site's relationship with NT.""",
                    values=SITE_STATUS_OPTIONS,
                    default=SITE_STATUS_PENDING)

    client_name = ValidTextLine(title="The Client Display Name",
                                max_length=40,
                                min_length=1,
                                required=True)

    parent_site = interface.Attribute("The parent site of this site")
    parent_site.setTaggedValue('_ext_excluded_out', True)

    setup_state = Object(ISetupState,
                         title="The site setup state",
                         required=False)

    @interface.invariant
    def environment_invariant(self):
        if self.status != SITE_STATUS_PENDING and self.environment is None:
            raise interface.Invalid("If site status is not pending, environment must be given.")


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


class IHostLoadUpdatedEvent(interface.Interface):

    host = Object(IHost,
                  title="The host",
                  required=True)


class IHostKnownSitesEvent(interface.Interface):

    host = Object(IHost,
                  title="The host that has updated information",
                  required=True)

    site_ids = ListOrTuple(title=u"The site identifiers tied to this environment",
                           readonly=True)


class ILMSSiteCreatedEvent(interface.Interface):

    site = Object(ILMSSite,
                  title="The site object created.",
                  required=True)


class ICSVLMSSiteCreatedEvent(ILMSSiteCreatedEvent):
    """
    Indicates a site was created via a csv file.
    """


class INewLMSSiteCreatedEvent(ILMSSiteCreatedEvent):
    """
    Indicates this site is newly created.
    """


class ITrialLMSSiteCreatedEvent(INewLMSSiteCreatedEvent):
    """
    Indicates a user created a trial site.
    """


class ISupportLMSSiteCreatedEvent(INewLMSSiteCreatedEvent):
    """
    Indicates a site was created for another party.
    """


class ILMSSiteUpdatedEvent(interface.Interface):

    site = interface.Attribute("The site object modified.")

    original_values = interface.Attribute("A dictionary that storing the original values of attributes that are being changed.")

    external_values = interface.Attribute("A dictionary that storing the external values.")


class ILMSSiteSetupFinished(interface.Interface):
    """
    An event that fires when a site setup has finished.
    The setup_state field will be updated to reflect the current state
    of the site.
    """
    site = Object(ILMSSite,
                  title="The site object created.",
                  required=True)


class ILMSSiteOwnerCompletedSetupEvent(IObjectEvent):
    """
    An event fired when we detect the owner completed the initial
    setup of the site. Note this may be fired some time after the setup was
    actually completed. The known time of completion is available
    via the completed_at attribute.
    """
    site = Object(ILMSSite,
                  title="The site.",
                  required=True)

    completed_at = DateTime(title=u'The datetime the setup was completed at',
                            required=True)


class ICustomerVerifiedEvent(IObjectEvent):
    """
    An event that fires when a customer has been verified.
    """


class ISiteUsage(IContained, ILastModified):
    """
    Some useful metrics that indicate how much usage a site has
    in particular those values that may affect billing.
    """
    admin_usernames = UniqueIterable(title="The unique admin usernames using seats",
                                     required=False)

    admin_count = Int(title="The total number of admins in a site",
                      required=False)

    instructor_usernames = UniqueIterable(title="The unique instructor usernames using seats",
                                          required=False)

    instructor_count = Int(title="The total number of unique instructors in a site",
                           required=False)

    user_count = Int(title="The total number of users in a site",
                     required=False)

    course_count = Int(title="The total number of courses in a site",
                       required=False)

    scorm_package_count = Int(title="The total number of scorm packages in a site",
                              required=False)
