import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'dnspython',
    'gunicorn[gevent]',
    'nameparser',
    'Paste',
    'python-dateutil',
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'waitress',
    'pyramid_mako',
    'pyramid_retry',
    'pyramid_zodbconn',
    'transaction',
    'ZODB',
    'nti.app.pyramid_zope',
    'nti.containers @ git+ssh://git@github.com/NextThought/nti.containers',
    'nti.mailer @ git+ssh://git@github.com/NextThought/nti.mailer',
    'nti.base @ git+ssh://git@github.com/NextThought/nti.base',
    'nti.dublincore @ git+ssh://git@github.com/NextThought/nti.dublincore',
    'nti.links @ git+ssh://git@github.com/NextThought/nti.links',
    'nti.mimetype @  git+ssh://git@github.com/NextThought/nti.mimetype',
    'nti.ntiids @ git+ssh://git@github.com/NextThought/nti.ntiids',
    'nti.traversal @ git+ssh://git@github.com/NextThought/nti.traversal',
    'nti.environments.management @ git+ssh://git@github.com/NextThought/nti.environments.management',
    'pyramid-chameleon',
    'pyramid-mako',
    'pyramid-zcml',
    'pyramid_authstack',
    'pyjwt',
    'zope.interface',
    'zope.component',
    'nti.externalization',
    'nti.property',
    'nti.schema',
    'nti.transactions==3.1.0',
    'nti.wref==1.0.0',
    'zope.container',
    'zope.site',
    'zope.generations',
    'RelStorage',
    'zc.zlibstorage',
    'nti.i18n',
    'z3c.schema',
    'z3c.table',
    'zope.app.appsetup',
    'zope.annotation',
    'zope.generations',
    'zope.i18n',
    'zope.i18nmessageid',
    'zope.principalregistry',
    'zope.securitypolicy',
    'pyramid_zope_request',
    'hubspot3',
    'z3c.rml',
    'zope.cachedescriptors',
    'tabulate'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
    'pyhamcrest',
    'fudge',
    'zope.testing',
    'zope.testrunner',
    'nti.testing',
    'nti.fakestatsd'
]

docs_require = [
    'sphinx',
    'repoze.sphinx.autointerface',
    'zope.testrunner'
]

setup(
    name='nti.app.environments',
    version_format='{tag}.dev{commits}+{sha}',
    setup_requires=['very-good-setuptools-git-version'],
    description='NTI App Environments',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    namespace_packages=['nti'],
    include_package_data=True,
    package_data={
        '': ['*.ini','*.mako', '*.zcml'],
    },
    zip_safe=False,
    extras_require={
        'test': tests_require,
        'docs': docs_require,
        'postgresql': [
            'psycopg2'
        ],
        'postgresql-dev': [
            'psycopg2-binary'
        ]
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = nti.app.environments:main',
        ],
        "paste.filter_app_factory": [
            "ops_ping = nti.app.environments.wsgi_ping:ping_handler_factory",
        ],
        'console_scripts': [
            "nti_pserve=nti.app.environments.nti_gunicorn:main",
            "nti_list_sites=nti.app.environments.utils.nti_list_sites:main",
            "nti_ping_sites=nti.app.environments.utils.nti_ping_sites:main"
        ],
    },
)
