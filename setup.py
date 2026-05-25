from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='partscape',
    version='1.0.0',
    description='Auto-parts intelligence system for Commonwealth of Dominica fleet management',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Seityl Group Ltd.',
    author_email='info@seityl.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'requests>=2.28.0',
        'rapidfuzz>=3.0.0',
    ],
)
