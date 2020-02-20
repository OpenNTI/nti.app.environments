import uuid

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.cachedescriptors.property import readproperty

from zope.container.contained import Contained

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.wref.interfaces import IWeakRef

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import ACT_READ
from nti.app.environments.auth import ACT_REQUEST_TRIAL_SITE

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import ISetupState
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSitesContainer
from nti.app.environments.models.interfaces import ISetupStatePending
from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ISetupStateFailure

from nti.app.environments.utils import find_iface


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

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.triallicense'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


@interface.implementer(IEnterpriseLicense)
class EnterpriseLicense(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(IEnterpriseLicense)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.enterpriselicense'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)


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

    createFieldProperties(ILMSSite)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.site'

    id = alias('__name__')
    site_id = alias('id')

    def __acl__(self):
        result = [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                  (Allow, ACCOUNT_MANAGEMENT_ROLE, (ACT_READ,))]
        if self.owner:
            result.insert(0, (Allow, self.owner.email, (ACT_READ,)))
        return result

    def __init__(self, parent_site=None, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)
        self.parent_site = parent_site

    def _get_owner(self):
        owner = self._owner_ref() if self._owner_ref else None
        if find_iface(owner, ICustomersContainer) is None:
            return None
        return owner

    def _set_owner(self, owner):
        self._owner_ref = IWeakRef(owner) if owner else None

    owner = property(_get_owner, _set_owner)

    def _get_parent_site(self):
        parent = self._parent_ref() if self._parent_ref else None
        if find_iface(parent, ILMSSitesContainer) is None:
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
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, (ACT_READ, ACT_REQUEST_TRIAL_SITE))]

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

    createFieldProperties(ISiteUsage)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.siteusage'

    def __init__(self, *args, **kwargs):
        SchemaConfigured.__init__(self, *args, **kwargs)
        PersistentCreatedModDateTrackingObject.__init__(self)
