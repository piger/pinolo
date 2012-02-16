#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="pinolo",
    version="0.9",
    description="Pinolo, the naughty chat bot",
    author="sand",
    author_email="daniel@spatof.org",
    url="http://code.dyne.org/?r=pinolo",
    # xapian!
    install_requires=["gevent>=0.12.2", "SQLAlchemy>=0.6.3"],
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
