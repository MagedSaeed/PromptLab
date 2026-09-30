import os

from setuptools import setup

with open("requirements.txt") as f:
    required = f.read().splitlines()

with open("README.md") as readme_file:
    readme = readme_file.read()

setup(
    name="templator",
    version="0.0",
    url="https://github.com/zaidalyafeai/templator",
    discription="Template Creator",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Zaid Alyafeai",
    license="MIT",
    packages=["templator"],
    install_requires=required,
    python_requires=">=3.6",
    include_package_data=True,
    zip_safe=False,
)
