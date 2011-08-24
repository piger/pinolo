#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="pinolo",
    version="0.1",
    description="Pinolo, the naughty chat bot",
    author="sand",
    author_email="daniel@spatof.org",
    url="http://code.dyne.org",
    # xapian
    install_requires=["gevent", "SQLAlchemy"],
    setup_requires=[],
    zip_safe=False,
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "pinolo = pinolo.main:main",
        ],
    },
)
