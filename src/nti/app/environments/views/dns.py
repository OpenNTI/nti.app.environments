from pyramid.view import view_config

from nti.externalization.interfaces import LocatedExternalDict

from nti.environments.management.dns import is_dns_name_available

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.views.base import BaseView


@view_config(renderer='rest',
             context=IOnboardingRoot,
             request_method='GET',
             name="check_dns_name")
class CheckDNSNameAvailableView(BaseView):

    def _is_dns_name_available(self, dns_name):
        """
        A domain is available if a) there are know sites that use the domain
        and b) there isn't a dns reservation for it.
        """
        sites_folder = get_sites_folder(self.context,
                                        request=self.request)
        for site in sites_folder.values():
            if dns_name in site.dns_names or ():
                return False

        return is_dns_name_available(dns_name)

    def __call__(self):
        params = self.request.params
        dns_name = self._get_param('dns_name', params)

        is_available = self._is_dns_name_available(dns_name)

        result = LocatedExternalDict()
        result.__parent__ = self.context.__parent__
        result.__name__ = self.context.__name__
        result.update({'dns_name': dns_name,
                       'is_available': is_available})
        return result
