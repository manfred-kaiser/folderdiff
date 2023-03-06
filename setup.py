from setuptools import setup, find_packages
from os import path


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def get_version():
    from folderdiff.__version__ import version
    return version

setup(
    name='folderdiff',
    version=get_version(),
    author='Manfred Kaiser',
    author_email='manfred.kaiser@ssh-mitm.at',
    description=(
        'FolderDiff is a tool to compare unzipped archives (e.g. Wordpress installations) with their original zip archive or a clean source folder.'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords="folder compare diff",
    packages=find_packages(),
    url="https://github.com/ssh-mitm/folderdiff",
    project_urls={
        'Changelog': 'https://github.com/ssh-mitm/folderdiff/blob/master/CHANGELOG.md',
        'Source': 'https://github.com/ssh-mitm/folderdiff',
        'Tracker': 'https://github.com/ssh-mitm/folderdiff/issues',
    },
    python_requires='>= 3.7',
    entry_points={
        'console_scripts': [
            'folderdiff = folderdiff.cli:main'
        ]
    }
)
