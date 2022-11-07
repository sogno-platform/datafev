"""
The datafev framework


Copyright (C) 2022,
Institute for Automation of Complex Power Systems (ACS),
E.ON Energy Research Center (E.ON ERC),
RWTH Aachen University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import setuptools
from pathlib import Path

long_description = (Path(__file__).parent / "README.md").read_text()


with open('README.md') as f:
    long_description = f.read()

setuptools.setup(
    name="datafev",
    description="A Python framework for development and testing of management algorithms for electric vehicle charging infrastructures",
    version="1.0.0",
    author="Institute for Automation of Complex Power Systems (ACS),"
           "E.ON Energy Research Center (E.ON ERC),"
           "RWTH Aachen University",
    author_email="post_acs@eonerc.rwth-aachen.de",
    url="https://git.rwth-aachen.de/acs/public/automation/datafev",
    license="MIT",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    #package_data={"pycity_scheduling": ["data/*.txt"], "examples": ["*.ipynb"]},
    #data_files=[(".", ["LICENSE.txt", "README.md"])],
    install_requires=[
		"matplotlib==3.5.1",
		"numpy==1.21.5",
		"openpyxl==3.0.9",
		"pandas==1.4.2",
		"pyomo==6.4.1",
		"sphinx==4.4.0",
    ],
    # extras_require={
    #     "test": ["pytest==6.2.4"]
    # },
    platforms="any",
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
    ],
    zip_safe=False,
    python_requires=">=3.6",
)
