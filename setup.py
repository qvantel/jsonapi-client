from setuptools import setup, find_packages

setup(
    name="jsonapi_client",
    version='0.9.5',
    description="Comprehensive, yet easy-to-use, pythonic, ORM-like access to JSON API services",
    long_description=(open("README.rst").read() + "\n" +
                      open("CHANGES.rst").read()),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: BSD License",
    ],
    author="Tuomas Airaksinen",
    author_email="tuomas.airaksinen@qvantel.com",
    url="https://github.com/qvantel/jsonapi-client",
    keywords="JSONAPI JSON API client",
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
