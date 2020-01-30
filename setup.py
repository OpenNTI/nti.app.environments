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
    'RelStorage==3.0b3',
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
    'zope.cachedescriptors'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
    'pyhamcrest',
    'zope.testing',
    'zope.testrunner',
    'nti.testing'
]

docs_require = [
    'sphinx',
    'repoze.sphinx.autointerface',
    'zope.testrunner'
]

setup(
    name='nti.app.environments',
    version='0.0',
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
        'docs': docs_require
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = nti.app.environments:main',
        ],
        'console_scripts': [
            "nti_pserve=nti.app.environments.nti_gunicorn:main",
        ],
    },
)
