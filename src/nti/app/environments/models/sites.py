import uuid

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained

from nti.containers.containers import CaseInsensitiveCheckingLastModifiedBTreeContainer

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.schema import SchemaConfigured

from nti.wref.interfaces import IWeakRef

from nti.app.environments.auth import ADMIN_ROLE
from nti.app.environments.auth import ACCOUNT_MANAGEMENT_ROLE
from nti.app.environments.auth import ACT_READ

from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ICustomersContainer
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer

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


@interface.implementer(ILMSSite)
class PersistentSite(SchemaConfigured, PersistentCreatedModDateTrackingObject, Contained):

    createFieldProperties(ILMSSite)

    mimeType = mime_type = 'application/vnd.nextthought.app.environments.site'

    id = alias('__name__')

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


@interface.implementer(ILMSSitesContainer)
class SitesFolder(CaseInsensitiveCheckingLastModifiedBTreeContainer):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS),
                (Allow, ACCOUNT_MANAGEMENT_ROLE, ACT_READ)]

    def addSite(self, site, siteId=None):
        siteId = site.__name__ or siteId or _generate_site_id()
        self[siteId] = site
        return site

    def deleteSite(self, siteId):
        siteId = getattr(siteId, '__name__', siteId)
        del self[siteId]


def _generate_site_id():
    return 'S' + uuid.uuid4().hex
