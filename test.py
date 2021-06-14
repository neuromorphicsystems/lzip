import lzip
import pathlib
import tempfile
dirname = pathlib.Path(__file__).resolve().parent

# decompress_file_iter
length = 0
for chunk in lzip.decompress_file_iter(dirname / 'test_data.lz'):
    length += len(chunk)
assert length == 254

# decompress_file_iter with word size
length = 0
try:
    for chunk in lzip.decompress_file_iter(dirname / 'test_data.lz', word_size=100):
        length += len(chunk)
except lzip.RemainingBytesError as error:
    assert len(error.buffer) == 54
    length += len(error.buffer)
assert length == 254

# decompress_file
assert len(lzip.decompress_file(dirname / 'test_data.lz')) == 254

# decompress_file with word size
length = 0
try:
    length += lzip.decompress_file(dirname / 'test_data.lz', word_size=100)
except lzip.RemainingBytesError as error:
    assert len(error.buffer) == 54
    length += len(error.buffer)
assert length == 54

# decompress_buffer_iter
with open(dirname / 'test_data.lz', 'rb') as input_file:
    buffer = input_file.read()
length = 0
for chunk in lzip.decompress_buffer_iter(buffer):
    length += len(chunk)
assert length == 254

# decompress_buffer_iter with word size
with open(dirname / 'test_data.lz', 'rb') as input_file:
    buffer = input_file.read()
length = 0
try:
    for chunk in lzip.decompress_buffer_iter(buffer, word_size=100):
        length += len(chunk)
except lzip.RemainingBytesError as error:
    assert len(error.buffer) == 54
    length += len(error.buffer)
assert length == 254

# decompress_buffer
with open(dirname / 'test_data.lz', 'rb') as input_file:
    buffer = input_file.read()
assert len(lzip.decompress_buffer(buffer)) == 254

# decompress_buffer with word size
with open(dirname / 'test_data.lz', 'rb') as input_file:
    buffer = input_file.read()
length = 0
try:
    length += lzip.decompress_buffer(buffer, word_size=100)
except lzip.RemainingBytesError as error:
    assert len(error.buffer) == 54
    length += len(error.buffer)
assert length == 54

# decompress_url_iter
length = 0
for chunk in lzip.decompress_url_iter((dirname / 'test_data.lz').as_uri()):
    length += len(chunk)
assert length == 254

# decompress_url_iter with word size
length = 0
try:
    for chunk in lzip.decompress_url_iter((dirname / 'test_data.lz').as_uri(), word_size=100):
        length += len(chunk)
except lzip.RemainingBytesError as error:
    assert len(error.buffer) == 54
    length += len(error.buffer)
assert length == 254

# decompress_url
assert len(lzip.decompress_url((dirname / 'test_data.lz').as_uri())) == 254

# decompress_url with word size
length = 0
try:
    length += lzip.decompress_url((dirname /
                                  'test_data.lz').as_uri(), word_size=100)
except lzip.RemainingBytesError as error:
    assert len(error.buffer) == 54
    length += len(error.buffer)
assert length == 54

# BufferEncoder
with open(dirname / 'test_data', 'rb') as input_file:
    buffer = input_file.read()
length = 0
encoder = lzip.BufferEncoder()
length += len(encoder.compress(buffer[:100]))
length += len(encoder.compress(buffer[100:200]))
length += len(encoder.compress(buffer[200:]))
length += len(encoder.finish())
assert length == 198

# compress_to_buffer
with open(dirname / 'test_data', 'rb') as input_file:
    buffer = input_file.read()
assert len(lzip.compress_to_buffer(buffer)) == 198

# FileEncoder
with open(dirname / 'test_data', 'rb') as input_file:
    buffer = input_file.read()
with tempfile.TemporaryDirectory() as temporary_directory:
    path = pathlib.Path(temporary_directory) / 'test_data.lz'
    with lzip.FileEncoder(path) as encoder:
        encoder.compress(buffer[:100])
        encoder.compress(buffer[100:200])
        encoder.compress(buffer[200:])
    with open(path, 'rb') as encoded_file:
        assert len(encoded_file.read()) == 198

# compress_to_file
with open(dirname / 'test_data', 'rb') as input_file:
    buffer = input_file.read()
with tempfile.TemporaryDirectory() as temporary_directory:
    path = pathlib.Path(temporary_directory) / 'test_data.lz'
    lzip.compress_to_file(path, buffer)
    with open(path, 'rb') as encoded_file:
        assert len(encoded_file.read()) == 198
