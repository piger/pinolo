#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="pinolo",
    version="0.10.1",
    description="Pinolo, the naughty chat bot",
    author="sand",
    author_email="daniel@spatof.org",
    url="http://git.spatof.org/pinolo.git",
    # xapian!
    install_requires=[
        "SQLAlchemy==0.7.10",
        "PyStemmer==1.3.0",
        "Whoosh==2.3.2",
        "requests==1.2.0",
        "beautifulsoup4==4.1.3",
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
