from zope import interface


class IHubspotClientFactory(interface.Interface):

    def __call__():
        pass
