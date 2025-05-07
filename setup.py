"""Invenio Stats Dashboard."""

import os

from setuptools import find_packages, setup

readme = open("README.md").read()
history = open("CHANGES.md").read()

tests_require = [
    "pytest-invenio>=1.4.0",
]

extras_require = {
    "docs": [
        "Sphinx>=3,<4",
    ],
    "tests": tests_require,
}

extras_require["all"] = []
for reqs in extras_require.values():
    extras_require["all"].extend(reqs)

setup_requires = [
    "Babel>=2.8",
]

install_requires = [
    "invenio-base>=1.2.3",
    "invenio-assets>=1.2.0",
]

packages = find_packages()

# Get the version string. Cannot be done with import!
g = {}
with open(os.path.join("invenio_stats_dashboard", "version.py"), "rt") as fp:
    exec(fp.read(), g)
    version = g["__version__"]

setup(
    name="invenio-stats-dashboard",
    version=version,
    description=__doc__,
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/markdown",
    keywords="invenio stats dashboard",
    license="MIT",
    author="MESH Research",
    author_email="info@meshresearch.net",
    url="https://github.com/MESH-Research/invenio-stats-dashboard",
    packages=packages,
    zip_safe=False,
    include_package_data=True,
    platforms="any",
    entry_points={
        "invenio_base.apps": [
            "invenio_stats_dashboard = invenio_stats_dashboard:InvenioStatsDashboard",
        ],
        "invenio_assets.webpack": [
            "invenio_stats_dashboard = invenio_stats_dashboard.webpack:theme",
        ],
    },
    extras_require=extras_require,
    install_requires=install_requires,
    setup_requires=setup_requires,
    python_requires=">=3.8",
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Development Status :: 4 - Beta",
    ],
)
