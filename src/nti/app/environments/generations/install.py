#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generations for managing courses.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope.generations.generations import SchemaManager

generation = 0

logger = __import__('logging').getLogger(__name__)


class _EnvironmentSchemaManager(SchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        from IPython.core.debugger import Tracer; Tracer()()
        super(_EnvironmentSchemaManager, self).__init__(
            generation=generation,
            minimum_generation=generation,
            package_name='nti.app.environments.generations')


def install_root_folders(context):
    from IPython.core.debugger import Tracer; Tracer()()
    raise ValueError('Install Me')



def evolve(context):
    from IPython.core.debugger import Tracer; Tracer()()
    install_root_folders(context)
