import uuid

from persistent import Persistent

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained

from zope.container.folder import Folder

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
class SharedEnvironment(SchemaConfigured, Persistent, Contained):

    createFieldProperties(ISharedEnvironment)


@interface.implementer(IDedicatedEnvironment)
class DedicatedEnvironment(SchemaConfigured, Persistent, Contained):

    createFieldProperties(IDedicatedEnvironment)


@interface.implementer(ITrialLicense)
class TrialLicense(SchemaConfigured, Persistent, Contained):

    createFieldProperties(ITrialLicense)


@interface.implementer(IEnterpriseLicense)
class EnterpriseLicense(SchemaConfigured, Persistent, Contained):

    createFieldProperties(IEnterpriseLicense)


@interface.implementer(ILMSSite)
class PersistentSite(SchemaConfigured, Persistent, Contained):

    createFieldProperties(ILMSSite)

    id = alias('__name__')

    def _get_owner(self):
        owner = self._owner_ref() if self._owner_ref else None
        if find_iface(owner, ICustomersContainer) is None:
            return None
        return owner

    def _set_owner(self, owner):
        self._owner_ref = IWeakRef(owner) if owner else None

    owner = property(_get_owner, _set_owner)


@interface.implementer(ILMSSitesContainer)
class SitesFolder(Folder):

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
