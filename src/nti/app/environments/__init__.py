# NOTE: We must not import *anything* before the patch
import gevent; gevent.config.resolver = 'dnspython'
import gevent.monkey
gevent.monkey.patch_all()

from nti.app.environments._monkey import patch
patch()

from zope.component import getGlobalSiteManager

import zope.i18nmessageid as zope_i18nmessageid

from nti.externalization.extension_points import set_external_identifiers

from .appserver import OnboardingServer

from .interfaces import IOnboardingServer

from .configure import configure

# TODO what setup is missing here to make this work
MessageFactory = zope_i18nmessageid.MessageFactory('nti.app.environments')

# Override the hook in nti.ntiids,
# such that no OID/NTIIDs returned for externalization.
import nti.ntiids
def set_hook():
    hook = getattr(set_external_identifiers, 'sethook')
    hook(lambda context, result: None)
set_hook()


def main(global_config, **settings):
    """
    This function returns a Pyramid WSGI application.
    """
    config = configure(settings)

    # We've let pyramid_zodbconn open the databases and set them in the registry
    # https://github.com/Pylons/pyramid_zodbconn/blob/68419e05a19acfc611e1dd81f79acc2a88d6e81d/pyramid_zodbconn/__init__.py#L190
    # Our OnboardingServer object will handle the rest of the setup and registration.
    #
    # Another approach is to use our own zodb_conn_tween like we do for other apps. One noticible difference
    # is that tween is able to put the transaction in explicit mode before a connection is open. I don't see
    # a hook in zodbconn that would let us do that. That may not matter for this use case.

    # Create and register our onboarding server
    server = OnboardingServer(config.registry._zodb_databases)
    getGlobalSiteManager().registerUtility(server, IOnboardingServer)

    return config.make_wsgi_app()
