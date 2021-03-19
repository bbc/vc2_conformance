import os

from setuptools import setup, find_packages

version_file = os.path.join(os.path.dirname(__file__), "vc2_conformance", "version.py")
with open(version_file, "r") as f:
    exec (f.read())  # noqa: E211

readme_file = os.path.join(os.path.dirname(__file__), "README.md")
with open(readme_file, "r") as f:
    long_description = f.read()

setup(
    name="vc2_conformance",
    version=__version__,  # noqa: F821 -- loaded by 'exec' above
    packages=find_packages(),
    include_package_data=True,
    url="https://github.com/bbc/vc2_conformance",
    author="BBC R&D",
    description="Conformance testing utilities for the VC-2 video codec.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL-3.0-only",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="vc2 dirac dirac-pro conformance",
    install_requires=[
        # NB: bitarray-hardbyte is used in place of official 'bitarray' package
        # due to provision of a binary wheel.
        "bitarray-hardbyte",
        "sentinels",
        "vc2_data_tables >=0.1.1, <2.0",
        "vc2_bit_widths >=0.1.1, <2.0",
        "vc2_conformance_data >=0.1.1, <2.0",
        # Use old versions/polyfill libraries which have deprecated older Python
        # version support
        "enum34; python_version<'3.4'",
        "pillow<7; python_version<'3.0'",
        "pillow; python_version>='3.0'",
        "numpy<1.17; python_version<'3.0'",
        "numpy<1.20; python_version>='3.0' and python_version<'3.7'",
        "numpy; python_version>='3.7'",
    ],
    entry_points={
        "console_scripts": [
            "vc2-bitstream-viewer=vc2_conformance.scripts.vc2_bitstream_viewer:main",
            "vc2-bitstream-validator=vc2_conformance.scripts.vc2_bitstream_validator:main",
            "vc2-test-case-generator=vc2_conformance.scripts.vc2_test_case_generator:main",
            "vc2-test-case-generator-worker=vc2_conformance.scripts.vc2_test_case_generator.worker:main",
            "vc2-picture-explain=vc2_conformance.scripts.vc2_picture_explain:main",
            "vc2-picture-compare=vc2_conformance.scripts.vc2_picture_compare:main",
        ],
    },
)
