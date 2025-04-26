from setuptools import find_packages
from setuptools import setup

version = '2.11.0'

install_requires = [
    # We specify the minimum acme and certbot version as the current plugin
    # version for simplicity. See
    # https://github.com/certbot/certbot/issues/8761 for more info.
    f'acme>={version}',
    f'certbot>={version}',
    'importlib_resources>=1.3.1; python_version < "3.9"',
    'python-augeas',
    'setuptools>=41.6.0',
]

dev_extras = [
# TODO: python3-haproxyadmin
]

test_extras = [
    'pytest',
]

long_description = (
    "This is a plugin for Certbot, it enables automatically authenticating "
    "domains ans retrieving certificates. It can also restart HAProxy after "
    "new certificates are installed. However, it will not configure HAProxy "
    "because. HAProxy is unlikely to be used for small/simple setups like what"
    " Apache or NGiNX are more likely to be used for. HAProxy configurations "
    "vary greatly, any configuration this plugin could define is most likely "
    "not applicable in your environment."
)

haproxy_authenticator = 'certbot_haproxy.authenticator:HAProxyAuthenticator'

setup(
    name='certbot-haproxy',
    version=version,
    description="HAProxy plugin for Certbot",
    long_description=long_description,
    url='https://code.greenhost.net/open/certbot-haproxy',
    author="Greenhost BV",
    author_email='lehaproxy@greenhost.net',
    license='Apache License 2.0',
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],

    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'dev': dev_extras,
        'test': test_extras,
    },
    entry_points={
        'certbot.plugins': [
            'haproxy-authenticator = certbot_haproxy.authenticator:HAProxyAuthenticator',
        ],
    },
)
