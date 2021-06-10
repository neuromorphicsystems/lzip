# Lzip

A simple Python library to decode Lzip archives chunk by chunk.
See https://www.nongnu.org/lzip/ for details on the Lzip format.

```sh
pip3 install lzip
```

## Documentation

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

The size of each chunk is around 64 KiB and varies from one chunk to the next. To facilitate the parsing (post Lzip-decoding) of files that use fixed-sized words, `decoder` takes an optional parameter `chunk_factor`. The size of each chunk is still variable, but is guaranteed to be a multipe of `chunk_factor`. If the total size `n` of the archive is not a multiple of `chunk_factor`, the last `n - int(n / chunk_factor) * chunk_factor` bytes are dropped.

The following example decodes the archive `'/path/to/archive.lz'` and converts the decoded bytes to 4-bytes unsigned integers:
```py
import lzip
import numpy

for chunk in lzip.decoder('/path/to/archive.lz', 4):
    values = numpy.frombuffer(chunk, dtype='<u4')
```

## Publish

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
