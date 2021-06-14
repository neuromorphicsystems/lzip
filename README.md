A simple Python library to encode and decode Lzip archives chunk by chunk.
See https://www.nongnu.org/lzip/ for details on the Lzip format.

```sh
pip3 install lzip
```

# Quickstart

## Compress

Compress an in-memory buffer and write it to a file:
```py
import lzip

lzip.compress_to_file('/path/to/output.lz', b'data to compress')
```

Compress multiple chunks and write the result to a single file (useful when streaming data):
```py
import lzip

with lzip.FileEncoder('/path/to/output.lz') as encoder:
    encoder.compress(b'data')
    encoder.compress(b' to')
    encoder.compress(b' compress')
```

Use `FileEncoder` without `with`:
```py
import lzip

encoder = lzip.FileEncoder('/path/to/output.lz')
encoder.compress(b'data')
encoder.compress(b' to')
encoder.compress(b' compress')
encoder.close()
```

`lzip` can also compress data to in-memory buffers and use different compression levels. See the [detailed documentation](#documentation) below for such use-cases.

## Decompress

Read and decompress a file to an in-memory buffer:
```py
import lzip

buffer = lzip.decompress_file('/path/to/input.lz')
```

Read and decompress a file one chunk at a time (useful for large files):
```py
import lzip

for chunk in lzip.decompress_file_iter('/path/to/input.lz'):
    # chunk is a bytes object
```

Read and decompress a file one chunk at a time, and ensure that each chunk contains a number of bytes that is a multiple of `word_size` (useful to parse numpy arrays with a known dtype):
```py
import lzip
import numpy

for chunk in lzip.decompress_file_iter('/path/to/input.lz', word_size=4):
    values = numpy.frombuffer(chunk, dtype='<u4')
```

`lzip` can also download and decompress data from a URL or from an in-memory buffer. See the [detailed documentation](#documentation) below for such use-cases.

# Documentation

- [lzip](#lzip)
  - [FileEncoder](#fileencoder)
  - [BufferEncoder](#bufferencoder)
  - [RemainingBytesError](#RemainingBytesError)
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
  - [Decoder](#Decoder)
  - [Encoder](#Encoder)

## lzip

### FileEncoder

### BufferEncoder

### RemainingBytesError

### compress_to_buffer

### compress_to_file

### decompress_buffer

### decompress_buffer_iter

### decompress_file

### decompress_file_iter

### decompress_file_like

### decompress_file_like_iter

### decompress_url

### decompress_url_iter

## lzip_extension

### Decoder

### Encoder

The `decoder` class can be used to read the chunks in a file:
```py
import lzip

for chunk in lzip.decoder('/path/to/archive.lz'):
    # process chunk
```

`chunk` is a byte sequence (https://docs.python.org/3/library/stdtypes.html#bytes).

Since `decoder` is an iterator, the chunks can also be loaded as follows:
```py
import lzip

chunk_iterator = iter(lzip.decoder('/path/to/archive.lz'))

chunk_0 = next(chunk_iterator)
chunk_1 = next(chunk_iterator)
...
chunk_n = next(chunk_iterator)
```
When the end of the archive is reached, `next(chunk_iterator)` raises a `StopIteration` exception.

The size of each chunk is around 64 KiB and varies from one chunk to the next. To facilitate the parsing of files that use fixed-sized words, `decoder` takes an optional parameter `chunk_factor`. When this parameter is set, the size of each chunk remains variable but is guaranteed to be a multiple of `chunk_factor`. If the total size `n` of the uncompressed archive is not a multiple of `chunk_factor`, `lzip.RemainingBytesError` is raised after iterating over the last chunk.

The following example decodes the archive `'/path/to/archive.lz'` and converts the decoded bytes to 4-bytes unsigned integers:
```py
import lzip
import numpy

try:
    for chunk in lzip.decoder('/path/to/archive.lz', 4):
        values = numpy.frombuffer(chunk, dtype='<u4')
except lzip.RemainingBytesError as error:
    print(error) # prints 'RemainingBytesError: the total number of bytes is not a multiple of 4 (k remaining)'
                 # where k is in [0, 3]
    # the remaining bytes are stored in error.remaining_bytes
```

# Publish

1. Bump the version number in *setup.py*.

2. Install Cubuzoa in a different directory (https://github.com/neuromorphicsystems/cubuzoa) to build pre-compiled versions for all major operating systems. Cubuzoa depends on VirtualBox (with its extension pack) and requires about 75 GB of free disk space.
```
cd cubuzoa
python3 cubuzoa.py provision
python3 cubuzoa.py build /path/to/event_stream
```

3. Install twine
```
pip3 install twine
```

4. Upload the compiled wheels and the source code to PyPI:
```
python3 setup.py sdist --dist-dir wheels
python3 -m twine upload wheels/*
```
