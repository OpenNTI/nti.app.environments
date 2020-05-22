import uuid

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

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.schema.interfaces import IBeforeSchemaFieldAssignedEvent

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.wref.interfaces import IWeakRef

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import OPS_ROLE
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_REQUEST_TRIAL_SITE
from nti.app.environments.auth import ACT_SITE_LOGIN

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

from nti.app.environments.subscriptions.auth import ACT_STRIPE_MANAGE_SUBSCRIPTION

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


@interface.implementer(ITrialLicense)
class TrialLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ITrialLicense)

    license_name = u'trial'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.triallicense'

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

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IGrowthLicense)
class GrowthLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IGrowthLicense)

    license_name = u'growth'

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.growthlicense'

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

    def _get_owner(self):
        owner = self._owner_ref() if self._owner_ref else None
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
        return [(Deny, Everyone, ACT_STRIPE_MANAGE_SUBSCRIPTION),
                (Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, (ACT_READ, ACT_REQUEST_TRIAL_SITE)),
                (Allow, OPS_ROLE, (ACT_READ, ACT_REQUEST_TRIAL_SITE, ACT_SITE_LOGIN))]

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

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)
