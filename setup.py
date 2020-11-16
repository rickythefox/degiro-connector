from setuptools import setup, find_packages
setup(
    name='degiro-connector',
    version='0.0.3',
    packages=find_packages(),
    install_requires=[
        'wheel',
        'click',
        'grpcio',
        'protobuf',
        'requests',
        'wrapt',
        'orjson',
    ],
    author='Chavithra PARANA',
    author_email='chavithra@gmail.com',
    entry_points={
        'console_scripts': [
            'quotecast = quotecast.applications.cli:cli',
            'trading = trading.applications.cli:cli',
        ],
    }
)