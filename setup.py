from setuptools import setup, find_packages

setup(
    name='scanlib',
    version=open('VERSION').read().strip(),
    author='Francesco De Carlo',
    url='https://github.com/xray-imaging/scanlib',
    packages=find_packages(),
    include_package_data = True,
    description='Module to support scans',
    zip_safe=False,
)