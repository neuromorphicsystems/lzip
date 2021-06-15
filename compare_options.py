import argparse
import concurrent.futures
import operator
import lzip_extension
import matplotlib.pyplot
from mpl_toolkits.mplot3d import Axes3D
import pathlib
import sys

parser = argparse.ArgumentParser(description='Compare encoding options')
parser.add_argument('file', help='Uncompressed input file')
parser.add_argument('--chunk-size', type=int, default=(1 << 16), help='Input file chunk size')
args = parser.parse_args()
args.file = pathlib.Path(args.file)

dictionary_sizes = [65535, 1 << 12, 1 << 20, 3 << 19, 1 << 21, 3 << 20, 1 << 22, 1 << 23, 1 << 24, 3 << 23, 1 << 25]
match_len_limits = [5, 6, 8, 12, 16, 20, 36, 68, 132, 192, 273]

# calculate compression ratios
encoders = []
for dictionary_size in dictionary_sizes:
    for match_len_limit in match_len_limits:
        encoders.append([dictionary_size, match_len_limit, 0, lzip_extension.Encoder(dictionary_size, match_len_limit)])
total_size = 0
def compress_with(encoder_and_buffer):
    encoder_and_buffer[0][2] += len(encoder_and_buffer[0][3].compress(encoder_and_buffer[1]))
with concurrent.futures.ThreadPoolExecutor() as executor:
    total_size = args.file.stat().st_size
    bytes_read = 0
    with open(args.file, 'rb') as input_file:
        while True:
            buffer = input_file.read(args.chunk_size)
            bytes_read += len(buffer)
            sys.stdout.write(f'\r{(bytes_read / total_size) * 100:.2f} % ({bytes_read} / {total_size})')
            sys.stdout.flush()
            if len(buffer) == 0:
                break
            for _ in executor.map(compress_with, ((encoder, buffer) for encoder in encoders)):
                pass
sys.stdout.write('\n')
sys.stdout.flush()
for encoder in encoders:
    encoder[2] += len(encoder[3].finish())
    del encoder[3]
    encoder[2] = total_size / encoder[2]

# print the best ratio
best_encoder = max(encoders, key=operator.itemgetter(2))
print(f'best encoding: dictionary_size={best_encoder[0]}, match_len_limit={best_encoder[1]} ({best_encoder[2]:.2f}:1 compression ratio)')

# plot all ratios
figure = matplotlib.pyplot.figure()
subplot = figure.add_subplot(111, projection='3d')
subplot.scatter(
    [encoder[0] for encoder in encoders],
    [encoder[1] for encoder in encoders],
    [encoder[2] for encoder in encoders])
subplot.set_xlabel('dictionary size')
subplot.set_ylabel('match length')
subplot.set_zlabel('compression ratio')
matplotlib.pyplot.show()
