from abc import ABCMeta
from abc import abstractmethod

from zope import component
from zope import interface

from nti.externalization.interfaces import IExternalObjectDecorator
from nti.externalization.interfaces import StandardExternalFields

from nti.links import Link

from nti.property.property import alias

from nti.app.environments.auth import ACT_CREATE, is_admin_or_account_manager

from nti.app.environments.models.interfaces import ICustomer, ILMSSite
from nti.app.environments.models.interfaces import ISetupStateSuccess

from nti.app.environments.models.externalization import SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY

from nti.app.environments.views.traversal import SitesCollection


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

    def _predicate(self, context, unused_result):
        return context.email == self.request.authenticated_userid

    def _do_decorate_external(self, context, external):
        links = external.setdefault(StandardExternalFields.LINKS, [])
        link = Link(context, rel='sites', elements=('sites',))
        links.append(link)

        if self.request.has_permission(ACT_CREATE, SitesCollection(context, self.request)):
            external['can_create_new_site'] = True


@component.adapter(ILMSSite)
@interface.implementer(IExternalObjectDecorator)
class SiteInfoDecorator(AbstractRequestAwareDecorator):

    def _predicate(self, unused_context, unused_result):
        return is_admin_or_account_manager(self.request.authenticated_userid, self.request)

    def _do_decorate_external(self, context, external):
        for attr_name in SITE_FIELDS_EXTERNAL_FOR_ADMIN_ONLY:
            if attr_name not in external:
                external[attr_name] = getattr(context, attr_name)

@component.adapter(ILMSSite)
@interface.implementer(IExternalObjectDecorator)
class ContinueLinkDecorator(AbstractRequestAwareDecorator):

    
    def _predicate(self, context, unused_result):
        """
        Only the owner of the site gets this link
        """
        return context.owner.email == self.request.authenticated_userid \
            and ISetupStateSuccess.providedBy(context.setup_state)

    def _do_decorate_external(self, context, external):
        links = external.setdefault(StandardExternalFields.LINKS, [])

        link = Link(context, elements=('@@continue_to_site', ), rel='setup.continue')
        links.append(link)

    


