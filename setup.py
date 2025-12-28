# setup.py
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR


from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pacsat-ground-station",
    version="1.0.0",
    author="PACSAT Revival Project",
    description="A modern revival of the PACSAT store-and-forward satellite ground station",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pacsat-ground-station",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/pacsat-ground-station/issues",
        "Documentation": "https://github.com/yourusername/pacsat-ground-station/tree/main/docs",
        "Source Code": "https://github.com/yourusername/pacsat-ground-station",
    },
    packages=find_packages(include=["pacsat", "PyHamREST1", "PyAX25_22", "PyXKISS", "PyAGW3"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Telecommunications Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Ham Radio",
        "Topic :: System :: Networking",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pacsat-groundstation=pacsat.groundstation:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.md"],
    },
    keywords="pacsat amateur-radio satellite store-and-forward ax25 ftl0 kiss agwpe",
    license="GPLv3",
    platforms=["any"],
)
