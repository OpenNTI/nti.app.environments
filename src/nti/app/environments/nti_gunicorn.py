"""
A hack to help us ensure that we are loading and monkey-patching
the entire system before Pyramid loads.

NOTE: You shouldn't need to use this entry point unless you are
preloading with gunicorn and gevent.

"""

logger = __import__('logging').getLogger(__name__)

import sys
from pkg_resources import load_entry_point


def main():
    sys.exit(
        load_entry_point('gunicorn', 'console_scripts', 'gunicorn')()
    )


if __name__ == '__main__':
    sys.exit(main())
