import os
import uuid

from persistent.mapping import PersistentMapping

from pyramid.security import Allow
from pyramid.security import Deny
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import Everyone

from zope import component
from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.container.contained import Contained

from zope.schema.fieldproperty import FieldPropertyStoredThroughField

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.persistence import NoPickle

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.schema.field import Int
from nti.schema.field import Bool
from nti.schema.field import ValidTextLine
from nti.schema.field import Variant

from nti.schema.interfaces import IBeforeSchemaFieldAssignedEvent

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.wref.interfaces import IWeakRef

from nti.app.environments.models import IOnboardingRoot

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import OPS_ROLE
from nti.app.environments.auth import ACT_LIST
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_REQUEST_TRIAL_SITE
from nti.app.environments.auth import ACT_SITE_LOGIN
from nti.app.environments.auth import ACT_SITE_JWT_TOKEN
from nti.app.environments.auth import ACT_VIEW_SITE_USAGE

from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import ISetupState
from nti.app.environments.models.interfaces import ISiteLicense
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IStarterLicense
from nti.app.environments.models.interfaces import IGrowthLicense
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ISetupStateFailure
from nti.app.environments.models.interfaces import ISiteOperationalExtraData
from nti.app.environments.models.interfaces import IInstallableCourseArchive

from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_SUBSCRIPTION
from nti.app.environments.subscriptions.auth import ACT_STRIPE_LINK_SUBSCRIPTION

from nti.traversal.traversal import find_interface


@interface.implementer(ISharedEnvironment)
class SharedEnvironment(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ISharedEnvironment)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.sharedenvironment'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IDedicatedEnvironment)
class DedicatedEnvironment(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IDedicatedEnvironment)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.dedicatedenvironment'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


SMALL_SCORM_PACKAGE_LIMIT = 10
ZERO_SCORM_PACKAGE_LIMIT = 0

@interface.implementer(ITrialLicense)
class TrialLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ITrialLicense)

    license_name = u'trial'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.triallicense'

    @property
    def max_scorm_packages(self):
        return SMALL_SCORM_PACKAGE_LIMIT

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IEnterpriseLicense)
class EnterpriseLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IEnterpriseLicense)

    license_name = u'enterprise'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.enterpriselicense'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IStarterLicense)
class StarterLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IStarterLicense)

    license_name = u'starter'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.starterlicense'

    @property
    def max_scorm_packages(self):
        return ZERO_SCORM_PACKAGE_LIMIT

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IGrowthLicense)
class GrowthLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IGrowthLicense)

    license_name = u'growth'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.growthlicense'

    @property
    def max_scorm_packages(self):
        return SMALL_SCORM_PACKAGE_LIMIT

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

@component.adapter(ISiteLicense, ILMSSite, IBeforeSchemaFieldAssignedEvent)
def _attach_license_to_site(license, site, event):
    license.__parent__ = site


@interface.implementer(ISetupState)
class AbstractSetupState(SchemaConfigured,
                         PersistentCreatedModDateTrackingObject,
                         Contained):

    createDirectFieldProperties(ISetupState)

    __external_can_create__ = False

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

    @property
    def elapsed_time(self):
        result = None
        if self.start_time and self.end_time:
            result = (self.end_time - self.start_time).total_seconds()
        return result


@interface.implementer(ISetupStatePending)
class SetupStatePending(AbstractSetupState):

    createDirectFieldProperties(ISetupStatePending)

    state_name = u'pending'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.setupstatepending'


@interface.implementer(ISetupStateSuccess)
class SetupStateSuccess(AbstractSetupState):

    createDirectFieldProperties(ISetupStateSuccess)

    state_name = u'success'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.setupstatesuccess'


@interface.implementer(ISetupStateFailure)
class SetupStateFailure(AbstractSetupState):

    createDirectFieldProperties(ISetupStateFailure)

    state_name = u'failed'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.setupstatefailure'


@interface.implementer(ILMSSite)
class PersistentSite(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ILMSSite, omit='license')

    license = FieldPropertyStoredThroughField(ILMSSite['license'])

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.site'

    id = alias('__name__')
    site_id = alias('id')

    def __acl__(self):
        result = [(Deny, Everyone, ACT_STRIPE_MANAGE_SUBSCRIPTION),
                  (Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                  (Allow, ACCOUNT_MANAGEMENT_ROLE, (ACT_READ,)),
                  (Allow, OPS_ROLE, (ACT_READ,))]
        if self.owner:
            result.insert(0, (Allow, self.owner.email, (ACT_READ, ACT_STRIPE_MANAGE_SUBSCRIPTION)))
        return result

    def __init__(self, parent_site=None, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)
        self.parent_site = parent_site

    def _p_repr(self):
        return repr(f"PersistentSite({self.site_id})")

    def _get_owner(self):
        # Resolving our IWeakRef for our owner involves getting the customers folder
        # which in turns requires an IOnboardingRoot. If not provided we look for
        # one in the current request. That means this doesn't work outside the context
        # of a request (i.e. in a seperate transaction runner). Find our root, and provide
        # that if we can. There is an assumption here about the implementation of the IWeakRef
        # we have here. That's probably ok? We use a similar tightly coupled pattern with the
        # ICachingWeakRef in other places.
        root = find_interface(self, IOnboardingRoot, strict=False)
        owner = self._owner_ref(root=root) if self._owner_ref else None
        if find_interface(owner, ICustomersContainer, strict=False) is None:
            return None
        return owner

    def _set_owner(self, owner):
        self._owner_ref = IWeakRef(owner) if owner else None

    owner = property(_get_owner, _set_owner)

    def _get_parent_site(self):
        parent = self._parent_ref() if self._parent_ref else None
        if find_interface(parent, ILMSSitesContainer, strict=False) is None:
            return None
        return parent

    def _set_parent_site(self, parent):
        if parent is not None:
            if not ILMSSite.providedBy(parent):
                raise interface.Invalid("Invalid parent site type.")
            if parent is self:
                raise interface.Invalid("parent site can not be self.")

        self._parent_ref = IWeakRef(parent) if parent else None

    parent_site = property(_get_parent_site, _set_parent_site)

    @readproperty
    def client_name(self):
        return next(iter(self.dns_names)) if self.dns_names else None


@interface.implementer(ILMSSitesContainer)
class SitesFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ACT_STRIPE_LINK_SUBSCRIPTION),
                (Deny, Everyone, ACT_STRIPE_LINK_SUBSCRIPTION),
                (Deny, Everyone, ACT_STRIPE_MANAGE_SUBSCRIPTION),
                (Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, (ACT_READ,
                                                  ACT_LIST,
                                                  ACT_REQUEST_TRIAL_SITE,
                                                  ACT_VIEW_SITE_USAGE)),
                (Allow, OPS_ROLE, (ACT_READ,
                                   ACT_LIST,
                                   ACT_REQUEST_TRIAL_SITE,
                                   ACT_SITE_LOGIN,
                                   ACT_SITE_JWT_TOKEN,
                                   ACT_VIEW_SITE_USAGE))]

    def addSite(self, site, siteId=None):
        siteId = site.__name__ or siteId or _generate_site_id()
        self[siteId] = site
        return site

    def deleteSite(self, siteId):
        siteId = getattr(siteId, '__name__', siteId)
        del self[siteId]


def _generate_site_id():
    return 'S' + uuid.uuid4().hex


@interface.implementer(ISiteUsage)
class SiteUsage(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createDirectFieldProperties(ISiteUsage)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.siteusage'

    @property
    def admin_count(self):
        return None if self.admin_usernames is None else len(self.admin_usernames)

    @property
    def instructor_count(self):
        return None if self.instructor_usernames is None else len(self.instructor_usernames - self.admin_usernames)

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)

_CONVERTERS = (
    ('fromUnicode', str), #we only care about py3
    ('fromBytes', bytes),
    ('fromObject', object)
)

@interface.implementer(ISiteOperationalExtraData)
class SiteOperationalExtraData(Contained, PersistentMapping):

    _key_field = ValidTextLine(max_length=44)
    _key_field.__name__ = 'SiteOperationalExtraDataKey'
    
    _value_field = Variant([Int(), ValidTextLine(max_length=144), Bool()]) # order here matters because of Varient.fromObject.
    _value_field.__name__ = 'SiteOperationalExtraDataValue'

    def _transform_field(self, field, val):
        bound_field = field.bind(self)
        for meth_name_kind in _CONVERTERS:
            if isinstance(val, meth_name_kind[1]):
                meth = getattr(field, meth_name_kind[0], None)
                if meth is not None:
                    val = meth(val)
                    break
        else:
            # Here if we do not break out of the loop.
            field.validate(val)
    
        return val

    def _transform(self, key, value):
        if self._key_field:
            key = self._transform_field(self._key_field, key)

        if self._value_field:
            value = self._transform_field(self._value_field, value)
        
        return key, value

    def __setitem__(self, key, value):
        key, value = self._transform(key, value)
        return super(SiteOperationalExtraData, self).__setitem__(key, value)
        
@NoPickle
@interface.implementer(IInstallableCourseArchive)
class NonPeristentFileSystemBackedInstallableCourseArchive(object):

    createDirectFieldProperties(IInstallableCourseArchive, omit='absolute_path')

    @property
    def absolute_path(self):
        settings = component.getUtility(IOnboardingSettings)
        return os.path.join(settings['installable_content_archive_dir'], self.filename)
    
    def __init__(self, name=None, filename=None):
        self.name = name
        self.filename = filename
