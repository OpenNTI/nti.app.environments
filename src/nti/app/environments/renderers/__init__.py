"""
This package is copied in it's entirety from nti.dataserver:nti.app.renderers.

The following non general components have been stripped away:

1. Removed adapters.py (and tests) containing display name adapters.

"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from nti.app.authentication.who_classifiers import CLASS_BROWSER
