from zope import interface


class IHubspotClient(interface.Interface):

    def __call__():
        pass


class IBearerTokenFactory(interface.Interface):
    """
    An object that can provide bearer tokens
    for a given site. Typically registered as an adapter
    from ILMSSite
    """

    def make_bearer_token(username, realname=None, email=None, ttl=None):
        """
        Returns a bearer token for the provided user.

        ttl is the optional time the token should live. A value of none indicates
        no ttl. A numeric value is the number of seconds from now that the token should
        expire. If the ttl kwarg is not provided it may be defaulted to a sensible value.
        """
