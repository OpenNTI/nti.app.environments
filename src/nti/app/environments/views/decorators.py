from abc import ABCMeta
from abc import abstractmethod

from zope import component
from zope import interface

from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.links import Link

from nti.property.property import alias

from nti.app.environments.models.interfaces import ICustomer
from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.auth import is_admin_or_account_manager


class AbstractRequestAwareDecorator(object):
    """
    A base class providing support for decorators that
    are request-aware. Subclasses can be registered
    as either :class:`.IExternalMappingDecorator` objects
    or :class:`.IExternalObjectDecorator` objects and this
    class will unify the interface.
    """

    __metaclass__ = ABCMeta

    def __init__(self, unused_context, request):
        self.request = request

    def _predicate(self, unused_context, unused_result):
        """
        You may implement this method to check a precondition, return False if no decoration.
        """
        return True

    def decorateExternalMapping(self, context, result):
        if self._predicate(context, result):
            self._do_decorate_external(context, result)

    decorateExternalObject = alias('decorateExternalMapping')

    @abstractmethod
    def _do_decorate_external(self, context, result):
        """
        Implement this to do your actual decoration
        """
        raise NotImplementedError()


@component.adapter(ICustomer)
@interface.implementer(IExternalObjectDecorator)
class CustomerSitesLinkDecorator(AbstractRequestAwareDecorator):

    def _has_existing_sites(self, owner):
        for site in get_sites_folder(request=self.request).values():
            if site.owner == owner:
                return True
        return False

    def _do_decorate_external(self, context, external):
        links = external.setdefault(StandardExternalFields.LINKS, [])
        link = Link(context, rel='sites', elements=('sites',))
        links.append(link)

        if context.email != self.request.authenticated_userid:
            return

        if is_admin_or_account_manager(context.email, self.request) or not self._has_existing_sites(context):
            external['can_create_new_site'] = True
