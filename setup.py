from setuptools import setup, find_packages

setup(
    name="nb-jsonapi-client",
    version='0.9.9',
    description="Comprehensive, yet easy-to-use, pythonic, ORM-like access to JSON API services on NationBuilder",
    long_description=(open("README.rst").read() + "\n" +
                      open("CHANGES.rst").read()),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: BSD License",
    ],
    author="Dennis Hennen",
    author_email="dsh@dsh.org",
    url="https://github.com/dsh/nb-jsonapi-client",
    keywords="JSONAPI JSON API client NationBuilder",
    license="BSD-3",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "requests",
        "jsonschema",
        "aiohttp",
    ],
)
