`lzip` is a Python wrapper for lzlib (https://www.nongnu.org/lzip/lzlib.html) to encode and decode Lzip archives (https://www.nongnu.org/lzip/).

This package is compatible with arbitrary byte sequences but provides features to facilitate interoperability with Numpy's `frombuffer` and `tobytes` functions. Decoding and encoding can be performed in chunks, enabling the decompression, processing and compression of files that do not fit in RAM. URLs can be used as well to download, decompress and process the chunks of a remote Lzip archive in one go.

```sh
pip3 install lzip
```

# Quickstart

## Compress

Compress an in-memory buffer and write it to a file:
```py
import lzip

lzip.compress_to_file("/path/to/output.lz", b"data to compress")
```

Compress multiple chunks and write the result to a single file (useful to avoid large in-memory buffers):
```py
import lzip

with lzip.FileEncoder("/path/to/output.lz") as encoder:
    encoder.compress(b"data")
    encoder.compress(b" to")
    encoder.compress(b" compress")
```

Use `FileEncoder` without context management (`with`):
```py
import lzip

encoder = lzip.FileEncoder("/path/to/output.lz")
encoder.compress(b"data")
encoder.compress(b" to")
encoder.compress(b" compress")
encoder.close()
```

Compress a Numpy array and write the result to a file:
```py
import lzip
import numpy

values = numpy.arange(100, dtype="<u4")

lzip.compress_to_file("/path/to/output.lz", values.tobytes())
```

`lzip` can use different compression levels. See the [documentation](#documentation) below for details.

## Decompress

Read and decompress a file to an in-memory buffer:
```py
import lzip

buffer = lzip.decompress_file("/path/to/input.lz")
```

Read and decompress a file one chunk at a time (useful for large files):
```py
import lzip

for chunk in lzip.decompress_file_iter("/path/to/input.lz"):
    # chunk is a bytes object
```

Read and decompress a file one chunk at a time, and ensure that each chunk contains a number of bytes that is a multiple of `word_size` (useful to parse numpy arrays with a known dtype):
```py
import lzip
import numpy

for chunk in lzip.decompress_file_iter("/path/to/input.lz", word_size=4):
    values = numpy.frombuffer(chunk, dtype="<u4")
```

Download and decompress data from a URL:
```py
import lzip

# option 1: store the whole decompressed file in a single buffer
buffer = lzip.decompress_url("http://download.savannah.gnu.org/releases/lzip/lzip-1.22.tar.lz")

# option 2: iterate over the decompressed file in small chunks
for chunk in lzip.decompress_url_iter("http://download.savannah.gnu.org/releases/lzip/lzip-1.22.tar.lz"):
    # chunk is a bytes object
```

`lzip` can also decompress data from an in-memory buffer. See the [documentation](#documentation) below for details.

# Documentation

The present package contains two libraries. `lzip` deals with high-level operations (open and close files, download remote data, change default arguments...) whereas `lzip_extension` focuses on efficiently compressing and decompressing in-memory byte buffers.

`lzip` uses `lzip_extension` internally. The latter should only be used in advanced scenarios where fine buffer control is required.

- [lzip](#lzip)
  - [FileEncoder](#fileencoder)
  - [BufferEncoder](#bufferencoder)
  - [RemainingBytesError](#remainingbyteserror)
  - [compress_to_buffer](#compress_to_buffer)
  - [compress_to_file](#compresstofile)
  - [decompress_buffer](#decompress_buffer)
  - [decompress_buffer_iter](#decompress_buffer_iter)
  - [decompress_file](#decompress_file)
  - [decompress_file_iter](#decompress_file_iter)
  - [decompress_file_like](#decompress_file_like)
  - [decompress_file_like_iter](#decompress_file_like_iter)
  - [decompress_url](#decompress_url)
  - [decompress_url_iter](#decompress_url_iter)
- [lzip_extension](#lzip_extension)
  - [Decoder](#decoder)
  - [Encoder](#encoder)
- [Word size and remaining bytes](word-size-and-remaining-bytes)
- [Default parameters](default-paramters)
- [Compare options](compare-options)

## lzip

### FileEncoder

```py
class FileEncoder:
    def __init__(self, path, level=6, member_size=(1 << 51)):
        """
        Encode sequential byte buffers and write the compressed bytes to a file
        - path is the output file name, it must be a path-like object such as a string or a pathlib path
        - level must be either an integer in [0, 9] or a tuple (directory_size, match_length)
          0 is the fastest compression level, 9 is the slowest
          see https://www.nongnu.org/lzip/manual/lzip_manual.html for the mapping between
          integer levels, directory sizes and match lengths
        - member_size can be used to change the compressed file's maximum member size
          see the Lzip manual for details on the tradeoffs incurred by this value
        """

    def compress(self, buffer):
        """
        Encode a buffer and write the compressed bytes into the file
        - buffer must be a byte-like object, such as bytes or a bytearray
        """

    def close(self):
        """
        Flush the encoder contents and close the file

        compress must not be called after calling close
        Failing to call close results in a corrupted encoded file
        """
```

`FileEncoder` can be used as a context manager (`with FileEncoder(...) as encoder`). `close` is called automatically in this case.

### BufferEncoder

```py
class BufferEncoder:
    def __init__(self, level=6, member_size=(1 << 51)):
        """
        Encode sequential byte buffers and return the compressed bytes as in-memory buffers
        - level: see FileEncoder
        - member_size: see FileEncoder
        """

    def compress(self, buffer):
        """
        Encode a buffer and return the compressed bytes as an in-memory buffer
        - buffer must be a byte-like object, such as bytes or a bytearray
        This function returns a bytes object

        The compression algorithm may decide to buffer part or all of the data,
        hence the relationship between input (non-compressed) buffers and
        output (conpressed) buffers is not one-to-one
        In particular, the returned buffer can be empty (b"") even if the input buffer is not
        """

    def finish(self):
        """
        Flush the encoder contents
        This function returns a bytes object

        compress must not be called after calling finish
        Failing to call finish results in corrupted encoded buffers
        """
```

### RemainingBytesError

```py
class RemainingBytesError(Exception):
    def __init__(self, word_size, buffer):
        """
        Raised by decompress_* functions if the total number of bytes is not a multiple of word_size
        The remaining bytes are stored in self.buffer
        See "Word size and remaining bytes" for details
        """
```

### compress_to_buffer

```py
def compress_to_buffer(buffer, level=6, member_size=(1 << 51)):
    """
    Encode a single buffer and return the compressed bytes as an in-memory buffer
    - buffer must be a byte-like object, such as bytes or a bytearray
    - level: see FileEncoder
    - member_size: see FileEncoder
    This function returns a bytes object
    """
```

### compress_to_file

```py
def compress_to_file(path, buffer, level=6, member_size=(1 << 51)):
    """
    Encode a single buffer and write the compressed bytes into a file
    - path is the output file name, it must be a path-like object such as a string or a pathlib path
    - buffer must be a byte-like object, such as bytes or a bytearray
    - level: see FileEncoder
    - member_size: see FileEncoder
    """
```

### decompress_buffer

```py
def decompress_buffer(buffer, word_size=1):
    """
    Decode a single buffer and return the decompressed bytes as an in-memory buffer
    - buffer must be a byte-like object, such as bytes or a bytearray
    - word_size: see "Word size and remaining bytes"
    This function returns a bytes object
    """
```

### decompress_buffer_iter

```py
def decompress_buffer_iter(buffer, word_size=1):
    """
    Decode a single buffer and return an in-memory buffer iterator
    - buffer must be a byte-like object, such as bytes or a bytearray
    - word_size: see "Word size and remaining bytes"
    This function returns a bytes object iterator
    """
```

### decompress_file

```py
def decompress_file(path, word_size=1, chunk_size=(1 << 16)):
    """
    Read and decode a file and return the decompressed bytes as an in-memory buffer
    - path is the input file name, it must be a path-like object such as a string or a pathlib path
    - word_size: see "Word size and remaining bytes"
    - chunk_size: the number of bytes to read from the file at once
      large values increase memory usage but very small values impede performance
    This function returns a bytes object
    """
```

### decompress_file_iter

```py
def decompress_file_iter(path, word_size=1, chunk_size=(1 << 16)):
    """
    Read and decode a file and return an in-memory buffer iterator
    - path is the input file name, it must be a path-like object such as a string or a pathlib path
    - word_size: see "Word size and remaining bytes"
    - chunk_size: see decompress_file
    This function returns a bytes object iterator
    """
```

### decompress_file_like

```py
def decompress_file_like(file_like, word_size=1, chunk_size=(1 << 16)):
    """
    Read and decode a file-like object and return the decompressed bytes as an in-memory buffer
    - file_like is a file-like object, such as a file or a HTTP response
    - word_size: see "Word size and remaining bytes"
    - chunk_size: see decompress_file
    This function returns a bytes object
    """
```

### decompress_file_like_iter

```py
def decompress_file_like_iter(file_like, word_size=1, chunk_size=(1 << 16)):
    """
    Read and decode a file-like object and return an in-memory buffer iterator
    - file_like is a file-like object, such as a file or a HTTP response
    - word_size: see "Word size and remaining bytes"
    - chunk_size: see decompress_file
    This function returns a bytes object iterator
    """
```

### decompress_url

```py
def decompress_url(
    url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, cafile=None, capath=None, context=None,
    word_size=1,
    chunk_size=(1 << 16)):
    """
    Download and decode data from a URL and return the decompressed bytes as an in-memory buffer
    - url must be a string or a urllib.Request object
    - data, timeout, cafile, capath and context are passed to urllib.request.urlopen
      see https://docs.python.org/3/library/urllib.request.html for details
    - word_size: see "Word size and remaining bytes"
    - chunk_size: see decompress_file
    This function returns a bytes object
    """
```

### decompress_url_iter

```py
def decompress_url_iter(
    url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, cafile=None, capath=None, context=None,
    word_size=1,
    chunk_size=(1 << 16)):
    """
    Download and decode data from a URL and return an in-memory buffer iterator
    - url must be a string or a urllib.Request object
    - data, timeout, cafile, capath and context are passed to urllib.request.urlopen
      see https://docs.python.org/3/library/urllib.request.html for details
    - word_size: see "Word size and remaining bytes"
    - chunk_size: see decompress_file
    This function returns a bytes object iterator
    """
```

## lzip_extension

Even though `lzip_extension` behaves like a conventional Python module, it is written in C++. To keep the implementation simple, only positional arguments are supported (keyword arguments do not work). The Python classes documented below are equivalent to the classes exported by this low-level implementation.

You can use `lzip_extension` by importing it like any other module. *lzip.py* uses it extensively.

### Decoder

```py
class Decoder:
    def __init__(self, word_size=1):
        """
        Decode sequential byte buffers and return the decompressed bytes as in-memory buffers
        - word_size is a non-zero positive integer
          all the output buffers contain a number of bytes that is a multiple of word_size
        """

    def decompress(self, buffer):
        """
        Decode a buffer and return the decompressed bytes as an in-memory buffer
        - buffer must be a byte-like object, such as bytes or a bytearray
        This function returns a bytes object

        The compression algorithm may decide to buffer part or all of the data,
        hence the relationship between input (compressed) buffers and
        output (decompressed) buffers is not one-to-one
        In particular, the returned buffer can be empty (b"") even if the input buffer is not
        """

    def finish(self):
        """
        Flush the encoder contents
        This function returns a tuple (buffer, remaining_bytes)
          Both buffer and remaining_bytes and bytes objects
          buffer should be empty (b"") unless the file was truncated
          remaining_bytes is empty (b"") unless the total number of bytes decoded
          is not a multiple of word_size

        decompress must not be called after calling finish
        Failing to call finish delays garbage collection which can be an issue
        when decoding many files in a row, and prevents the algorithm from detecting
        remaining bytes (if the size is not a multiple of word_size)
        """
```

### Encoder

```py
class Encoder:
    def __init__(self, dictionary_size=(1 << 23), match_len_limit=36, member_size=(1 << 51)):
        """
        Encode sequential byte buffers and return the compressed bytes as in-memory buffers
        - dictionary_size is an integer in the range [(1 << 12), (1 << 29)]
        - match_len_limit is an integer in the range [5, 273]
        - member_size is an integer in the range [(1 << 12), (1 << 51)]
        """

    def compress(self, buffer):
        """
        Encode a buffer and return the compressed bytes as an in-memory buffer
        - buffer must be a byte-like object, such as bytes or a bytearray
        This function returns a bytes object

        The compression algorithm may decide to buffer part or all of the data,
        hence the relationship between input (decompressed) buffers and
        output (compressed) buffers is not one-to-one
        In particular, the returned buffer can be empty (b"") even if the input buffer is not
        """

    def finish(self):
        """
        Flush the encoder contents
        This function returns a bytes object

        compress must not be called after calling finish
        Failing to call finish results in corrupted encoded buffers
        """
```

## Compare options

The script *compare_options.py* uses the `lzip` library to compare the compression ratio of different pairs (dictionary_size, match_len_limit). It runs multiple compressions in parallel and does not store the compressed bytes. About 3 GB of RAM are required to run the script. Processing time depends on the file size and the number of processors on the machine.

The script requires matplotlib (`pip3 install matplotlib`) to display the results.

```sh
python3 compare_options /path/to/uncompressed/file [--chunk-size=65536]
```


## Word size and remaining bytes

Decoding functions take an optional parameter `word_size` that defaults to `1`. Decoded buffers are guaranteed to contain a number of bytes that is a multiple of `word_size` to facilitate fixed-sized words parsing (for example `numpy.frombytes`). If the total size of the uncompressed archive is not a multiple of `word_size`, `lzip.RemainingBytesError` is raised after iterating over the last chunk. The raised exception provides access to the remaining bytes.

Non-iter decoding functions do not provide access to the decoded buffers if the total size is not a multiple of `word_size` (only the remaining bytes).

The following example decodes a file and converts the decoded bytes to 4-bytes unsigned integers:
```py
import lzip
import numpy

try:
    for chunk in lzip.decompress_file_iter("/path/to/archive.lz", 4):
        values = numpy.frombuffer(chunk, dtype="<u4")
except lzip.RemainingBytesError as error:
    # this block is executed only if the number of bytes in "/path/to/archive.lz"
    # is not a multiple of 4 (after decompression)
    print(error) # prints "The total number of bytes is not a multiple of 4 (k remaining)"
                 # where k is in [1, 3]
    # error.buffer is a bytes object and contains the k remaining bytes
```

## Default parameters

The default parameters in `lzip` functions are not constants, despite what is presented in the documentation. The actual implementation looks like this:

```py
def some_function(some_parameter=None):
    if some_parameter is None:
        some_paramter = some_paramter_default_value
```

This approach makes it possible to change default values at the module level at any time. For example:
```py
import lzip

lzip.compress_to_file("/path/to/output0.lz", b"data to compress") # encoded at level 6 (default)

lzip.default_level = 9

lzip.compress_to_file("/path/to/output1.lz", b"data to compress") # encoded at level 9
lzip.compress_to_file("/path/to/output2.lz", b"data to compress") # encoded at level 9

lzip_default_level = 0

lzip.compress_to_file("/path/to/output1.lz", b"data to compress") # encoded at level 0
```

`lzip` exports the following *default* default values:

```py
default_level = 6
default_word_size = 1
default_chunk_size = 1 << 16
default_member_size = 1 << 51
```

# Publish

1. Bump the version number in *setup.py*.

2. Install Cubuzoa in a different directory (https://github.com/neuromorphicsystems/cubuzoa) to build pre-compiled versions for all major operating systems. Cubuzoa depends on VirtualBox (with its extension pack) and requires about 75 GB of free disk space.
```sh
cd cubuzoa
python3 cubuzoa.py provision
python3 cubuzoa.py build /path/to/lzip --post /path/to/lzip/test.py
```

3. Install twine
```sh
pip3 install twine
```

4. Upload the compiled wheels and the source code to PyPI:
```sh
python3 setup.py sdist --dist-dir wheels
python3 -m twine upload wheels/*
```
