import builtins
import distutils.core
import pathlib
import setuptools
import shutil
import sys

def build_ext_factory(parameters):
    import setuptools.command.build_ext
    class build_ext(setuptools.command.build_ext.build_ext):
        def finalize_options(self):
            setuptools.command.build_ext.build_ext.finalize_options(self)
            builtins.__NUMPY_SETUP__ = False
            import numpy
            self.include_dirs.append(numpy.get_include())
    return build_ext(parameters)

with open('README.md') as file:
    long_description = file.read()

extra_args = []
if sys.platform == 'linux':
    extra_args += ['-std=c++11']
elif sys.platform == 'darwin':
    extra_args += ['-std=c++11','-stdlib=libc++']

setuptools.setup(
    name='lzip',
    version='0.1.0',
    url='https://github.com/neuromorphicsystems/lzip',
    author='Alexandre Marcireau',
    author_email='alexandre.marcireau@gmail.com',
    description='decompress lzip archives',
    long_description=long_description,
    long_description_content_type='text/markdown',
    setup_requires=['numpy'],
    install_requires=['numpy'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    ext_modules=[
        distutils.core.Extension(
            'lzip',
            language='cpp',
            sources=['lzip.cpp', str(pathlib.Path('third_party') / 'lzlib' / 'lzlib.cpp')],
            extra_compile_args=extra_args,
            extra_link_args=extra_args,
            include_dirs=[],
            libraries=[]),
    ],
    cmdclass={'build_ext': build_ext_factory})
