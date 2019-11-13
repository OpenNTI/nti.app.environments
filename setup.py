import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'waitress',
    'pyramid_retry',
    'pyramid_tm',
    'pyramid_zodbconn',
    'transaction',
    'ZODB',
    'nti.mailer',
    'pyramid-chameleon',
    'pyramid-mako',
    'pyramid-zcml',
    'zope.interface',
    'zope.component',
    'nti.schema',
    'zope.container',
    'zope.site',
    'zope.generations',
    'RelStorage==3.0b3',
    'zc.zlibstorage',
    'nti.i18n',
    'z3c.schema',
    'zope.i18n',
    'zope.i18nmessageid'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
    'pyhamcrest'
]

docs_require = [
    'sphinx',
    'repoze.sphinx.autointerface',
    'zope.testrunner'
]

setup(
    name='nti.onboarding',
    version='0.0',
    description='NTI Onboarding',
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
    zip_safe=False,
    extras_require={
        'testing': tests_require,
        'docs': docs_require
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = nti.onboarding:main',
        ],
    },
)
