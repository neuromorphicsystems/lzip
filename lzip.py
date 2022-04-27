import io
import pathlib
import socket
import typing
import urllib.request
import lzip_extension

default_level: int = 6
default_word_size: int = 1
default_chunk_size: int = 1 << 16
default_member_size: int = 1 << 51
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
    def __init__(self, word_size: int, buffer: bytes):
        self.buffer = buffer
        super().__init__(f"The total number of bytes is not a multiple of {word_size} ({len(buffer)} remaining)")


def decompress_file_like_iter(
    file_like, word_size: typing.Optional[int] = None, chunk_size: typing.Optional[int] = None
):
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


def decompress_file_like(file_like, word_size=None, chunk_size=None) -> bytes:
    return b"".join(buffer for buffer in decompress_file_like_iter(file_like, word_size, chunk_size))


def decompress_file_iter(path, word_size=None, chunk_size=None):
    with open(path, "rb") as input_file:
        yield from decompress_file_like_iter(input_file, word_size, chunk_size)


def decompress_file(path, word_size=None, chunk_size=None) -> bytes:
    with open(path, "rb") as input_file:
        return decompress_file_like(input_file, word_size, chunk_size)


def decompress_buffer_iter(buffer, word_size=None):
    yield from decompress_file_like_iter(io.BytesIO(buffer), word_size, chunk_size=len(buffer))


def decompress_buffer(buffer, word_size=None) -> bytes:
    return decompress_file_like(io.BytesIO(buffer), word_size, chunk_size=len(buffer))


def decompress_url_iter(
    url, data=None, timeout=None, cafile=None, capath=None, context=None, word_size=None, chunk_size=None
):
    if timeout is None:
        timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    with urllib.request.urlopen(url, data, timeout, cafile=cafile, capath=capath, context=context) as response:
        yield from decompress_file_like_iter(response, word_size, chunk_size)


def decompress_url(
    url, data=None, timeout=None, cafile=None, capath=None, context=None, word_size=None, chunk_size=None
) -> bytes:
    if timeout is None:
        timeout = socket._GLOBAL_DEFAULT_TIMEOUT
    with urllib.request.urlopen(url, data, timeout, cafile=cafile, capath=capath, context=context) as response:
        return decompress_file_like(response, word_size, chunk_size)


class BufferEncoder:
    def __init__(self, level: typing.Optional[int] = None, member_size: typing.Optional[int] = None):
        if level is None:
            level = default_level
        assert isinstance(level, (list, tuple, int))
        if isinstance(level, (list, tuple)):
            assert len(level) == 2
        else:
            assert level >= 0 and level < 10
            level = level_to_dictionary_size_and_match_len_limit[level]
        assert isinstance(level[0], int) and level[0] >= (1 << 12) and level[0] < (1 << 29)
        assert isinstance(level[1], int) and level[1] >= 5 and level[1] <= 273
        dictionary_size, match_len_limit = level
        if member_size is None:
            member_size = default_member_size
        self.encoder = lzip_extension.Encoder(dictionary_size, match_len_limit, member_size)

    def compress(self, buffer: bytes) -> None:
        return self.encoder.compress(buffer)

    def finish(self) -> bytes:
        result = self.encoder.finish()
        self.encoder = None
        return result


def compress_to_buffer(buffer, level: typing.Optional[int] = None, member_size: typing.Optional[int] = None) -> bytes:
    if level is None:
        level = default_level
    encoder = BufferEncoder(level, member_size)
    result = encoder.compress(buffer)
    result += encoder.finish()
    return result


class FileEncoder:
    def __init__(
        self,
        path: typing.Union[str, bytes, pathlib.Path],
        level: typing.Optional[int] = None,
        member_size: typing.Optional[int] = None,
    ):
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
            dictionary_size, match_len_limit = level_to_dictionary_size_and_match_len_limit[level]
        if member_size is None:
            member_size = default_member_size
        self.encoder = lzip_extension.Encoder(dictionary_size, match_len_limit, member_size)
        self.file = open(path, "wb")

    def compress(self, buffer: bytes) -> None:
        self.file.write(self.encoder.compress(buffer))

    def close(self) -> None:
        self.file.write(self.encoder.finish())
        self.encoder = None
        self.file.close()
        self.file = None

    def __enter__(self):
        return self

    def __exit__(self, type, *_):
        self.close()
        return type is None


def compress_to_file(
    path, buffer: bytes, level: typing.Optional[int] = None, member_size: typing.Optional[int] = None
) -> None:
    if level is None:
        level = default_level
    with FileEncoder(path, level, member_size) as encoder:
        encoder.compress(buffer)
