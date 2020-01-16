from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from nti.externalization.interfaces import IExternalReferenceResolver

from nti.app.environments.models.interfaces import ILMSSite
from nti.app.environments.models.interfaces import ISiteUsage
from nti.app.environments.models.interfaces import InvalidSiteError

from nti.app.environments.models.sites import SiteUsage

from nti.app.environments.models.utils import get_sites_folder

SITE_USAGE_ANNOTATION_KEY = 'SiteUsage'


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


def get_site_usage(site):
    return site_usage_factory(site, create=False)
