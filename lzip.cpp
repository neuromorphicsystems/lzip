#include "third_party/lzlib/lzlib.h"
#include <Python.h>
#include <fstream>
#include <string>
#include <structmember.h>
#include <vector>

constexpr std::size_t buffer_size = 1 << 20;

/// python_path_to_string converts a path-like object to a string.
std::string python_path_to_string(PyObject* path) {
    if (PyUnicode_Check(path)) {
        return reinterpret_cast<const char*>(PyUnicode_DATA(path));
    }
    {
        const auto characters = PyBytes_AsString(path);
        if (characters) {
            return characters;
        } else {
            PyErr_Clear();
        }
    }
    auto string_or_bytes = PyObject_CallMethod(path, "__fspath__", nullptr);
    if (string_or_bytes) {
        if (PyUnicode_Check(string_or_bytes)) {
            return reinterpret_cast<const char*>(PyUnicode_DATA(string_or_bytes));
        }
        const auto characters = PyBytes_AsString(string_or_bytes);
        if (characters) {
            return characters;
        } else {
            PyErr_Clear();
        }
    }
    throw std::runtime_error("path must be a string, bytes, or a path-like object");
}

void throw_lz_error(LZ_Decoder* lz_decoder) {
    throw std::runtime_error(LZ_strerror(LZ_decompress_errno(lz_decoder)));
}

/// decoder reads a Lzip archive.
struct decoder {
    std::size_t chunk_factor;
    PyObject_HEAD std::unique_ptr<std::ifstream> input;
    LZ_Decoder* lz_decoder;
    std::vector<uint8_t> buffer;
    std::vector<uint8_t> decoded_buffer;
};
void decoder_dealloc(PyObject* self) {
    auto current = reinterpret_cast<decoder*>(self);
    if (current->lz_decoder) {
        LZ_decompress_close(current->lz_decoder);
        current->lz_decoder = NULL;
    }
}
static PyObject* decoder_new(PyTypeObject* type, PyObject*, PyObject*) {
    return type->tp_alloc(type, 0);
}
static PyMemberDef decoder_members[] = {
    {nullptr, 0, 0, 0, nullptr},
};
static PyObject* decoder_iter(PyObject* self) {
    Py_INCREF(self);
    return self;
}
static PyObject* decoder_iternext(PyObject* self) {
    auto current = reinterpret_cast<decoder*>(self);
    try {
        for (;;) {
            if (current->input->eof()) {
                {
                    std::vector<uint8_t> empty;
                    current->buffer.swap(empty);
                }
                {
                    std::vector<uint8_t> empty;
                    current->decoded_buffer.swap(empty);
                }
                current->input.reset();
                if (current->lz_decoder) {
                    LZ_decompress_close(current->lz_decoder);
                    current->lz_decoder = NULL;
                }
                break;
            }
            {
                const auto size =
                    std::min(static_cast<int32_t>(buffer_size / 4), LZ_decompress_write_size(current->lz_decoder));
                current->buffer.resize(size);
                if (size > 0) {
                    current->input->read(reinterpret_cast<char*>(current->buffer.data()), current->buffer.size());
                    current->buffer.resize(current->input->gcount());
                    if (LZ_decompress_write(current->lz_decoder, current->buffer.data(), current->buffer.size())
                        != static_cast<int32_t>(current->buffer.size())) {
                        throw_lz_error(current->lz_decoder);
                        throw std::runtime_error("the LZ decoder did not consume all the bytes");
                    }
                    if (current->input->eof()) {
                        if (LZ_decompress_finish(current->lz_decoder) < 0) {
                            throw_lz_error(current->lz_decoder);
                        }
                    }
                }
            }
            current->buffer.resize(
                std::max(buffer_size, static_cast<std::size_t>(LZ_decompress_dictionary_size(current->lz_decoder))));
            for (;;) {
                const auto total_decompressed = LZ_decompress_total_in_size(current->lz_decoder);
                const auto decoded_bytes_read =
                    LZ_decompress_read(current->lz_decoder, current->buffer.data(), current->buffer.size());
                if (decoded_bytes_read < 0) {
                    throw_lz_error(current->lz_decoder);
                }
                if (decoded_bytes_read == 0) {
                    if (LZ_decompress_total_in_size(current->lz_decoder) == total_decompressed) {
                        break;
                    }
                    continue;
                }
                const auto current_size = current->decoded_buffer.size();
                current->decoded_buffer.resize(current_size + decoded_bytes_read);
                std::copy(
                    current->buffer.begin(),
                    std::next(current->buffer.begin(), decoded_bytes_read),
                    std::next(current->decoded_buffer.begin(), current_size));
            }
            const auto full_packets_size =
                (current->decoded_buffer.size() / current->chunk_factor) * current->chunk_factor;
            if (full_packets_size > 0) {
                auto bytes = PyBytes_FromStringAndSize(
                    reinterpret_cast<const char*>(current->decoded_buffer.data()),
                    static_cast<Py_ssize_t>(full_packets_size));
                if (current->decoded_buffer.size() == full_packets_size) {
                    current->decoded_buffer.clear();
                } else {
                    std::copy(
                        std::next(current->decoded_buffer.begin(), full_packets_size),
                        current->decoded_buffer.end(),
                        current->decoded_buffer.begin());
                    current->decoded_buffer.resize(current->decoded_buffer.size() - full_packets_size);
                }
                return bytes;
            }
        }
    } catch (const std::exception& exception) {
        PyErr_SetString(PyExc_RuntimeError, exception.what());
    }
    return nullptr;
}
static PyMethodDef decoder_methods[] = {
    {nullptr, nullptr, 0, nullptr},
};
static int decoder_init(PyObject* self, PyObject* args, PyObject* kwds) {
    PyObject* path;
    uint64_t chunk_factor = 1;
    if (!PyArg_ParseTuple(args, "O|K", &path, &chunk_factor)) {
        return -1;
    }
    auto current = reinterpret_cast<decoder*>(self);
    try {
        current->chunk_factor = chunk_factor;
        if (current->chunk_factor == 0) {
            throw std::runtime_error("chunk_factor cannot be zero");
        }
        const auto filename = python_path_to_string(path);
        current->input.reset(new std::ifstream(filename));
        if (!current->input->good()) {
            throw std::runtime_error(std::string("'") + filename + "' could not be open for reading");
        }
        current->lz_decoder = LZ_decompress_open();
        if (!current->lz_decoder) {
            current->input.reset();
            throw std::runtime_error("the LZ decompressor could not be allocated");
        }
        if (LZ_decompress_errno(current->lz_decoder) != LZ_ok) {
            current->input.reset();
            LZ_decompress_close(current->lz_decoder);
            throw std::runtime_error("initializing the LZ decompressor failed");
        }
        current->buffer.reserve(buffer_size);
        current->decoded_buffer.reserve(buffer_size);
    } catch (const std::exception& exception) {
        PyErr_SetString(PyExc_RuntimeError, exception.what());
        return -1;
    }
    return 0;
}
static PyTypeObject decoder_type = {PyVarObject_HEAD_INIT(nullptr, 0)};

static PyMethodDef lzip_methods[] = {{nullptr, nullptr, 0, nullptr}};
static struct PyModuleDef event_stream_definition =
    {PyModuleDef_HEAD_INIT, "lzip", "lzip decompresses lzip archives", -1, lzip_methods};
PyMODINIT_FUNC PyInit_lzip() {
    PyObject* module = PyModule_Create(&event_stream_definition);
    decoder_type.tp_name = "lzip.decoder";
    decoder_type.tp_basicsize = sizeof(decoder);
    decoder_type.tp_dealloc = decoder_dealloc;
    decoder_type.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
    decoder_type.tp_iter = decoder_iter;
    decoder_type.tp_iternext = decoder_iternext;
    decoder_type.tp_methods = decoder_methods;
    decoder_type.tp_members = decoder_members;
    decoder_type.tp_new = decoder_new;
    decoder_type.tp_init = decoder_init;
    PyType_Ready(&decoder_type);
    PyModule_AddObject(module, "decoder", (PyObject*)&decoder_type);
    return module;
}
