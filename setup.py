from setuptools import setup, find_packages

setup(
    name='simepics',
    version=open('VERSION').read().strip(),
    author='Francesco De Carlo',
    url='https://github.com/xray-imaging/simepics',
    packages=find_packages(),
    include_package_data = True,
    description='Module to control Additive Manufacturing at beamline 32-ID',
    zip_safe=False,
)