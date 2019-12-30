"""
A hack to help us ensure that we are loading and monkey-patching
the entire system before Pyramid loads
"""

# NOTE: We must not import *anything* before the patch
import gevent.monkey
gevent.monkey.patch_all()

logger = __import__('logging').getLogger(__name__)

import sys
from pkg_resources import load_entry_point


def main():
    sys.exit(
        load_entry_point('gunicorn', 'console_scripts', 'gunicorn')()
    )


if __name__ == '__main__':
    sys.exit(main())
