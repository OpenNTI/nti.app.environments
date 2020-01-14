from zope import interface

from nti.externalization.interfaces import IExternalReferenceResolver

from nti.app.environments.models.interfaces import InvalidSiteError
from nti.app.environments.models.utils import get_sites_folder


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
