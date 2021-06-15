import distutils.core
import pathlib
import setuptools
import sys

with open('README.md') as file:
    long_description = file.read()

extra_compile_args = []
extra_link_args = []
if sys.platform == 'linux':
    extra_compile_args += ['-std=c++11']
    extra_link_args += ['-std=c++11', '-lstdc++']
elif sys.platform == 'darwin':
    extra_compile_args += ['-std=c++11', '-stdlib=libc++']
    extra_link_args += ['-std=c++11', '-stdlib=libc++']

setuptools.setup(
    name='lzip',
    version='0.1.0',
    url='https://github.com/neuromorphicsystems/lzip',
    author='Alexandre Marcireau',
    author_email='alexandre.marcireau@gmail.com',
    description='decompress lzip archives',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    py_modules=['lzip'],
    ext_modules=[
        distutils.core.Extension(
            'lzip_extension',
            language='cpp',
            sources=['lzip_extension.cpp', str(
                pathlib.Path('third_party') / 'lzlib' / 'lzlib.cpp')],
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            include_dirs=[],
            libraries=[]),
    ])
