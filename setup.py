#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="pinolo",
    version="0.9.2",
    description="Pinolo, the naughty chat bot",
    author="sand",
    author_email="daniel@spatof.org",
    url="http://code.dyne.org/?r=pinolo",
    # xapian!
    install_requires=[
        "gevent==0.13.8",
        "greenlet==0.4.0",
        "SQLAlchemy==0.7.8",
        "requests==0.14.0",
        "beautifulsoup4==4.1.3"
    ],
    setup_requires=[],
    zip_safe=False,
    packages=find_packages(),
    package_data={
        "pinolo": ['data/*.txt', 'data/prcd/*',
                   'plugins/*.txt'
                  ],
    },
    entry_points={
        "console_scripts": [
            "pinolo = pinolo.main:main",
        ],
    },
)
