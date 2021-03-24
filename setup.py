from setuptools import setup, find_packages

setup(
    name='pymaniascript',
    version='0a1',
    description='Library that computes ASTs for Maniascript scripts.',
    author='MrLag',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.9'
    ],
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=['sly', 'robotpy-cppheaderparser==5.0.13'],
    python_requires='>=3.6'
)