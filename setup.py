#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="pinolo",
    version="0.10.3",
    description="Pinolo, the naughty chat bot",
    author="Daniel Kertesz",
    author_email="daniel@spatof.org",
    url="https://github.com/piger/pinolo",
    # xapian!
    install_requires=[
        'SQLAlchemy',
        'PyStemmer',
        'Whoosh',
        'requests',
        'beautifulsoup4',
    ],
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "pinolo = pinolo.main:main",
            "pinolo-train = pinolo.plugins.megahal:cmdline",
        ],
    },
)
