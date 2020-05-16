import contextlib

import time

from zope.app.publication.zopepublication import ZopePublication

from ..models import ROOT_KEY

logger = __import__('logging').getLogger(__name__)

@contextlib.contextmanager
def evolve_context(context, generation):
    logger.info('Starting evolution to generation %i', generation)
    start = time.time()
    root_folder = context.connection.root()[ZopePublication.root_name][ROOT_KEY]
    yield root_folder
    logger.info('Evolution %i completed in %s seconds', generation, time.time()-start)
