from setuptools import setup, find_packages

with open("vc2_conformance/version.py", "r") as f:
    exec(f.read())

setup(
    name="vc2_conformance",
    version=__version__,
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
    install_requires=["enum34", "bitarray", "sentinels", "sympy", "six", "vc2_data_tables"],
    entry_points = {
        'console_scripts': [
            'vc2-bitstream-viewer=vc2_conformance.scripts.vc2_bitstream_viewer:main',
            'vc2-bitstream-validator=vc2_conformance.scripts.vc2_bitstream_validator:main',
            'vc2-bitstream-generator=vc2_conformance.scripts.vc2_bitstream_generator:main',
        ],
    },
)
