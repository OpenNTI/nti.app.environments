from persistent import Persistent

from pyramid.security import Allow
from pyramid.security import ALL_PERMISSIONS

from zope import interface

from zope.container.contained import Contained
from zope.container.contained import NameChooser

from zope.container.folder import Folder
from zope.container.interfaces import INameChooser

from nti.property.property import alias
from nti.property.property import LazyOnClass

from nti.schema.fieldproperty import createFieldProperties
from nti.schema.schema import SchemaConfigured

from nti.app.environments.auth import ADMIN_ROLE

from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ILMSSitesContainer


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


@interface.implementer(ILMSSitesContainer)
class SitesFolder(Folder):

    @LazyOnClass
    def __acl__(self):
        return [(Allow, ADMIN_ROLE, ALL_PERMISSIONS)]

    def addSite(self, site):
        if not site.__name__:
            chooser = INameChooser(self)
            key = chooser.chooseName(site.owner_username, site)
            self[key] = site
        return site

    def deleteSite(self, key):
        key = getattr(key, '__name__', key)
        del self[key]


@interface.implementer(INameChooser)
class SitesNameChooser(NameChooser):
    pass
