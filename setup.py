import os

import sys

from setuptools import setup, find_packages

version_file = os.path.join(os.path.dirname(__file__), "vc2_conformance", "version.py")
with open(version_file, "r") as f:
    exec (f.read())  # noqa: E211

install_requires = [
    "enum34",
    "bitarray",
    "sentinels",
    "vc2_data_tables",
    "vc2_bit_widths",
    "vc2_conformance_data",
]

# Use old versions of libraries which have deprecated Python 2.7 support
if sys.version[0] == "2":
    install_requires.append("pillow<7")
    install_requires.append("numpy<1.17")
else:
    install_requires.append("pillow")
    install_requires.append("numpy")

setup(
    name="vc2_conformance",
    version=__version__,  # noqa: F821 -- loaded by 'exec' above
    packages=find_packages(),
    include_package_data=True,
    url="https://github.com/bbc/vc2_conformance",
    author="BBC R&D",
    description="Conformance testing utilities for the VC-2 video codec.",
    license="GPLv2",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
    keywords="smpte-RP-2042-3 vc2 dirac dirac-pro conformance",
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "vc2-bitstream-viewer=vc2_conformance.scripts.vc2_bitstream_viewer:main",
            "vc2-bitstream-validator=vc2_conformance.scripts.vc2_bitstream_validator:main",
            "vc2-test-case-generator=vc2_conformance.scripts.vc2_test_case_generator:main",
            "vc2-test-case-generator-worker=vc2_conformance.scripts.vc2_test_case_generator.worker:main",
            "vc2-raw-explain=vc2_conformance.scripts.vc2_raw_explain:main",
            "vc2-raw-compare=vc2_conformance.scripts.vc2_raw_compare:main",
        ],
    },
)
