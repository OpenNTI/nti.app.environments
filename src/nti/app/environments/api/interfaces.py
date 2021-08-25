from zope import interface

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

class ISiteUsageUpdater(interface.Interface):
    """
    A callable that can update the usage information of an associated site.
    """

    def __call__(site, nt_client):
        """
        Update the ISiteUsage information for the provided site, using
        the given client.
        """

class MissingDataserverSiteIdException(Exception):
    """
    An exception raised when the site used for JWT creation does not have
    a value assigned to ds_site_id
    """

class PlatformException(Exception):
    """
    An exception raised when an error occurs interacting with the platform
    """

class AuthenticatedSessionRequiredException(PlatformException):
    """
    Raised when an authenticated session is required or the session
    does not have the proper permissions.
    """

class MissingTargetException(PlatformException):
    """
    Raised when an expected target (workspace, collection, link, etc.)
    can't be found.
    """

class ISiteContentInstaller(interface.Interface):
    """
    Something that can install IInstallableCourseArchive in a site.
    Typically this would be adapted from an ILMSSite
    """

    def install_course_archive(archive):
        """
        Install the provided archive and return the json course
        that was created.
        """
        pass
