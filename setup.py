from setuptools import setup, find_packages

setup(
    name='aws-sso-sync',
    version='1.0.0',
    description='Automated AWS SSO Profile Synchronizer & Agent Mapper',
    author='Sebastian',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'aws-sso-sync=aws_sso_sync.cli:main',
        ],
    },
    install_requires=[],
    python_requires='>=3.6',
)