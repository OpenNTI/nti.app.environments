from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from zope.annotation.interfaces import IAnnotations

from nti.externalization.interfaces import IExternalReferenceResolver

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import InvalidSiteError
from nti.app.environments.models.interfaces import ISiteAuthTokenContainer
from nti.app.environments.models.interfaces import ISiteOperationalExtraData

from nti.app.environments.models.sites import SiteUsage
from nti.app.environments.models.sites import SiteOperationalExtraData

from nti.app.environments.models.utils import get_sites_folder
from nti.app.environments.models.utils import get_hosts_folder
from nti.app.environments.models.customers import SiteAuthTokenContainer

from nti.traversal.traversal import find_interface

SITE_USAGE_ANNOTATION_KEY = 'SiteUsage'
SITE_AUTHTOKEN_CONTAINER_ANNOTATION_KEY = 'SiteAuthTokenContainer'
SITE_OPERATIONAL_EXTRA_DATA_ANNOTATION_KEY = 'SiteOperationalExtraData'


@interface.implementer(IExternalReferenceResolver)
class ParentSiteResolver(object):

    def __init__(self, updating, to_resolve):
        pass

    def resolve(self, parent_site):
        parent_site_id = getattr(parent_site, 'id', parent_site)
        if isinstance(parent_site_id, str):
            parent_site = get_sites_folder().get(parent_site_id)
            if parent_site is None:
                raise InvalidSiteError("No parent site found: %s" % parent_site_id)
        return parent_site


@interface.implementer(IExternalReferenceResolver)
class HostResolver(object):

    def __init__(self, updating, to_resolve):
        pass

    def resolve(self, host):
        host_id = getattr(host, 'id', host)
        if isinstance(host_id, str):
            host = get_hosts_folder().get(host_id)
            if host is None:
                raise InvalidSiteError("No host found: %s" % host_id)
        return host


@component.adapter(ILMSSite)
@interface.implementer(ISiteUsage)
def site_usage_factory(site, create=True):
    result = None
    annotations = IAnnotations(site)
    try:
        result = annotations[SITE_USAGE_ANNOTATION_KEY]
    except KeyError:
        if create:
            result = SiteUsage()
            annotations[SITE_USAGE_ANNOTATION_KEY] = result
            result.__name__ = SITE_USAGE_ANNOTATION_KEY
            result.__parent__ = site
    return result

@component.adapter(ILMSSite)
@interface.implementer(ISiteOperationalExtraData)
def _extra_data_factory():
    return SiteOperationalExtraData()

OperationalExtraDataFactory = an_factory(_extra_data_factory,
                                         SITE_OPERATIONAL_EXTRA_DATA_ANNOTATION_KEY)

def get_site_usage(site):
    return site_usage_factory(site, create=False)

def site_from_license(license):
    return find_interface(license, ILMSSite, strict=False)


@component.adapter(ICustomer)
@interface.implementer(ISiteAuthTokenContainer)
def auth_token_container_factory(customer, create=True):
    result = None
    annotations = IAnnotations(customer)
    try:
        result = annotations[SITE_AUTHTOKEN_CONTAINER_ANNOTATION_KEY]
    except KeyError:
        if create:
            result = SiteAuthTokenContainer()
            annotations[SITE_AUTHTOKEN_CONTAINER_ANNOTATION_KEY] = result
            result.__name__ = SITE_AUTHTOKEN_CONTAINER_ANNOTATION_KEY
            result.__parent__ = customer
    return result
