import pathlib
import setuptools
import setuptools.extension
import setuptools.command.build_ext
import sys

dirname = pathlib.Path(__file__).resolve().parent

with open(dirname / "README.md") as file:
    long_description = file.read()

extra_compile_args = []
extra_link_args = []
if sys.platform == "linux":
    extra_compile_args += ["-std=c++17"]
    extra_link_args += ["-std=c++17", "-lstdc++"]
elif sys.platform == "darwin":
    extra_compile_args += ["-std=c++17", "-stdlib=libc++"]
    extra_link_args += ["-std=c++17", "-stdlib=libc++"]

exec(open(dirname / "version.py").read())
setuptools.setup(
    name="lzip",
    version=__version__,  # type: ignore
    url="https://github.com/neuromorphicsystems/lzip",
    author="Alexandre Marcireau",
    author_email="alexandre.marcireau@gmail.com",
    description="Lzip (.lz) archives compression and decompression with buffers and URLs support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    py_modules=["lzip"],
    ext_modules=[  # type: ignore
        setuptools.extension.Extension(
            "lzip_extension",
            language="cpp",
            sources=[
                "lzip_extension.cpp",
                str(dirname / "third_party" / "lzlib" / "lzlib.cpp"),
            ],
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            include_dirs=[],
            libraries=[],
        ),
    ],
)
