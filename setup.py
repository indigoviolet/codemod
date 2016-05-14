try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

description = (
    'modone is codemod, one file at a time'
)

setup(
    name='modone',
    version="1.0.0",
    url='http://github.com/indigoviolet/modone',
    license='Apache License 2.0',
    author="Venky Iyer",
    author_email="indigoviolet@gmail.com",
    description=description,
    long_description=description,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    entry_points='''
        [console_scripts]
        modone=modone.base:main
    ''',
    tests_require=['flake8', 'pytest'],
    test_suite='py.test'
)
