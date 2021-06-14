import argparse
import operator
import lzip_extension
import matplotlib.pyplot
from mpl_toolkits.mplot3d import Axes3D

parser = argparse.ArgumentParser(description='Compare encoding options')
parser.add_argument('file', help='Uncompressed input file')
parser.add_argument('--chunk-size', type=int, default=(1 << 16), help='Input file chunk size')
args = parser.parse_args()

dictionary_sizes = [65535, 1 << 12, 1 << 20, 3 << 19, 1 << 21, 3 << 20, 1 << 22, 1 << 23, 1 << 24, 3 << 23, 1 << 25]
match_len_limits = [5, 6, 8, 12, 16, 20, 36, 68, 132, 192, 273]

# calculate compression ratios
dictionary_size_to_match_len_limit_to_encoders_and_results = {dictionary_size: {
    match_len_limit: [lzip_extension.Encoder(
        dictionary_size, match_len_limit), 0]
    for match_len_limit
    in match_len_limits
} for dictionary_size in dictionary_sizes}
total_size = 0
with open(args.file, 'rb') as input_file:
    while True:
        buffer = input_file.read(args.chunk_size)
        if len(buffer) == 0:
            break
        total_size += len(buffer)
        for match_len_limit_to_encoders_and_results in dictionary_size_to_match_len_limit_to_encoders_and_results.values():
            for encoder_and_result in match_len_limit_to_encoders_and_results.values():
                encoder_and_result[1] += len(encoder_and_result[0].compress(buffer))
triplets = []
for dictionary_size, match_len_limit_to_encoders_and_results in dictionary_size_to_match_len_limit_to_encoders_and_results.items():
    for match_len_limit, encoder_and_result in match_len_limit_to_encoders_and_results.items():
        encoder_and_result[1] += len(encoder_and_result[0].finish())
        triplets.append((dictionary_size, match_len_limit, total_size / encoder_and_result[1]))

best_triplet = max(triplets, key=operator.itemgetter(2))
print(f'best encoding: dictionary_size={best_triplet[0]}, match_len_limit={best_triplet[1]} ({best_triplet[2]:.2f}:1 compression ratio)')

figure = matplotlib.pyplot.figure()
subplot = figure.add_subplot(111, projection='3d')
subplot.scatter(
    [triplet[0] for triplet in triplets],
    [triplet[1] for triplet in triplets],
    [triplet[2] for triplet in triplets])
subplot.set_xlabel('dictionary size')
subplot.set_ylabel('match length')
subplot.set_zlabel('compression ratio')
matplotlib.pyplot.show()
