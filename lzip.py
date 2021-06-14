import io
import lzip_extension
import socket
import urllib.request

default_level = 6
default_word_size = 1
default_chunk_size = 1 << 16
default_member_size = 1 << 51
level_to_dictionary_size_and_match_len_limit = {
    0: (65535, 16),
    1: (1 << 20, 5),
    2: (3 << 19, 6),
    3: (1 << 21, 8),
    4: (3 << 20, 12),
    5: (1 << 22, 20),
    6: (1 << 23, 36),
    7: (1 << 24, 68),
    8: (3 << 23, 132),
    9: (1 << 25, 273),
}


class RemainingBytesError(Exception):
    def __init__(self, word_size, bytes):
        self.message = f'The total number of bytes is not a multiple of {word_size} ({len(bytes)} remaining)'
        self.bytes = bytes


def decompress_file_like_iter(file_like, word_size=None, chunk_size=None):
    if word_size is None:
        word_size = default_word_size
    if chunk_size is None:
        chunk_size = default_chunk_size
    assert chunk_size > 0
    decoder = lzip_extension.Decoder(word_size)
    while True:
        encoded_bytes = file_like.read(chunk_size)
        if len(encoded_bytes) == 0:
            break
        decoded_bytes = decoder.decompress(encoded_bytes)
        if len(decoded_bytes) > 0:
            yield decoded_bytes
    decoded_bytes, remaining_bytes = decoder.finish()
    if len(decoded_bytes) > 0:
        yield decoded_bytes
    if len(remaining_bytes) > 0:
        raise RemainingBytesError(word_size, remaining_bytes)


def decompress_file_like(file_like, word_size=None, chunk_size=None):
    return b''.join(buffer for buffer in decompress_file_like_iter(file_like, word_size, chunk_size))


def decompress_file_iter(path, word_size=None, chunk_size=None):
    with open(path, 'rb') as input_file:
        yield from decompress_file_like_iter(input_file, word_size, chunk_size)


def decompress_file(path, word_size=None, chunk_size=None):
    with open(path, 'rb') as input_file:
        return decompress_file_like(input_file, word_size, chunk_size)


def decompress_buffer_iter(buffer, word_size=None):
    yield from decompress_file_like_iter(io.BytesIO(buffer), word_size, chunk_size=len(buffer))


def decompress_buffer(buffer, word_size=None):
    return decompress_file_like(io.BytesIO(buffer), word_size, chunk_size=len(buffer))


def decompress_url_iter(url, data=None, timeout=None, cafile=None, capath=None, context=None, word_size=None, chunk_size=None):
    if timeout is None:
        timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    with urllib.request.urlopen(url, data, timeout, cafile=cafile, capath=capath, context=context) as response:
        yield from decompress_file_like_iter(response, word_size, chunk_size)


def decompress_url(url, data=None, timeout=None, cafile=None, capath=None, context=None, word_size=None, chunk_size=None):
    if timeout is None:
        timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    with urllib.request.urlopen(url, data, timeout, cafile=cafile, capath=capath, context=context) as response:
        return decompress_file_like(response, word_size, chunk_size)


class BufferEncoder:
    def __init__(self, level=None, member_size=None):
        if level is None:
            level = default_level
        assert isinstance(level, (list, tuple, int))
        if isinstance(level, (list, tuple)):
            assert len(level) == 2
            assert level[0] >= (1 << 12) and level[0] < (1 << 29)
            assert level[1] >= 5 and level[1] <= 273
            dictionary_size, match_len_limit = level
        else:
            assert level >= 0 and level < 10
            dictionary_size, match_len_limit = level_to_dictionary_size_and_match_len_limit[
                level]
        if member_size is None:
            member_size = default_member_size
        self.encoder = lzip_extension.Encoder(
            dictionary_size, match_len_limit, member_size)

    def compress(self, buffer):
        return self.encoder.compress(buffer)

    def finish(self):
        result = self.encoder.finish()
        self.encoder = None
        return result


def compress_to_buffer(buffer, level=None, member_size=None):
    if level is None:
        level = default_level
    encoder = BufferEncoder(level, member_size)
    result = encoder.compress(buffer)
    result += encoder.finish()
    return result


class FileEncoder:
    def __init__(self, path, level=None, member_size=None):
        if level is None:
            level = default_level
        assert isinstance(level, (list, tuple, int))
        if isinstance(level, (list, tuple)):
            assert len(level) == 2
            assert level[0] >= (1 << 12) and level[0] < (1 << 29)
            assert level[1] >= 5 and level[1] <= 273
            dictionary_size, match_len_limit = level
        else:
            assert level >= 0 and level < 10
            dictionary_size, match_len_limit = level_to_dictionary_size_and_match_len_limit[
                level]
        if member_size is None:
            member_size = default_member_size
        self.encoder = lzip_extension.Encoder(
            dictionary_size, match_len_limit, member_size)
        self.file = open(path, 'wb')

    def compress(self, buffer):
        self.file.write(self.encoder.compress(buffer))

    def close(self):
        self.file.write(self.encoder.finish())
        self.encoder = None
        self.file.close()
        self.file = None

    def __enter__(self):
        return self

    def __exit__(self, type, *_):
        self.close()
        return type is None


def compress_to_file(path, buffer, level=None, member_size=None):
    if level is None:
        level = default_level
    with FileEncoder(path, level, member_size) as encoder:
        encoder.compress(buffer)
