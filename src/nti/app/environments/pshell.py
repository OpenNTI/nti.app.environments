from pyramid_zodbconn import get_connection

from . import models

from .models.interfaces import IOnboardingRoot


def setup(env):
    request = env['request']
    conn = get_connection(request)

    env['models'] = models
    env['conn'] = conn
    env['root'] = conn.root()
    env['onboarding'] = IOnboardingRoot(request)
