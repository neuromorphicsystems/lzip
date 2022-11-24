#include "../third_party/lzlib/lzlib.h"
#include <Python.h>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <structmember.h>
#include <vector>

constexpr int32_t internal_buffer_size = 1 << 16;

/// throw_lz_error raises a C++ exception from a lzlib error code.
void throw_lz_error(LZ_Decoder* lz_decoder) {
    throw std::runtime_error(std::string("Lzip error: ") + LZ_strerror(LZ_decompress_errno(lz_decoder)));
}
void throw_lz_error(LZ_Encoder* lz_encoder) {
    throw std::runtime_error(std::string("Lzip error: ") + LZ_strerror(LZ_compress_errno(lz_encoder)));
}

/// decoder decompresses Lzip buffers.
struct decoder {
    PyObject_HEAD std::size_t word_size;
    LZ_Decoder* lz_decoder;
    std::vector<uint8_t> decoded_buffer;
};
static void decoder_consume_all(decoder* current) {
    for (;;) {
        const auto previous_size = current->decoded_buffer.size();
        const auto free_space = std::max(internal_buffer_size, LZ_decompress_dictionary_size(current->lz_decoder));
        current->decoded_buffer.resize(previous_size + free_space);
        const auto total_decompressed = LZ_decompress_total_in_size(current->lz_decoder);
        const auto decoded_bytes_read =
            LZ_decompress_read(current->lz_decoder, current->decoded_buffer.data() + previous_size, free_space);
        if (decoded_bytes_read < 0) {
            current->decoded_buffer.resize(previous_size);
            throw_lz_error(current->lz_decoder);
        }
        if (decoded_bytes_read == 0) {
            current->decoded_buffer.resize(previous_size);
            if (LZ_decompress_total_in_size(current->lz_decoder) == total_decompressed) {
                break;
            }
            continue;
        }
        current->decoded_buffer.resize(previous_size + decoded_bytes_read);
    }
}
static PyObject* full_packets_bytes(decoder* current) {
    const auto full_packets_size = (current->decoded_buffer.size() / current->word_size) * current->word_size;
    if (full_packets_size > 0) {
        auto bytes = PyBytes_FromStringAndSize(
            reinterpret_cast<const char*>(current->decoded_buffer.data()), static_cast<Py_ssize_t>(full_packets_size));
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
    return PyBytes_FromString("");
}
static void decoder_dealloc(PyObject* self) {
    auto current = reinterpret_cast<decoder*>(self);
    {
        std::vector<uint8_t> empty;
        current->decoded_buffer.swap(empty);
    }
    if (current->lz_decoder) {
        LZ_decompress_close(current->lz_decoder);
        current->lz_decoder = nullptr;
    }
    Py_TYPE(self)->tp_free(self);
}
static PyObject* decoder_new(PyTypeObject* type, PyObject*, PyObject*) {
    return type->tp_alloc(type, 0);
}
static PyMemberDef decoder_members[] = {
    {nullptr, 0, 0, 0, nullptr},
};
static PyObject* decoder_decompress(PyObject* self, PyObject* args) {
    Py_buffer buffer;
    if (!PyArg_ParseTuple(args, "y*", &buffer)) {
        return nullptr;
    }
    auto thread_state = PyEval_SaveThread();
    auto current = reinterpret_cast<decoder*>(self);
    try {
        if (!current->lz_decoder) {
            throw std::runtime_error("decompress cannot be called after finish");
        }
        for (Py_ssize_t offset = 0; offset < buffer.len;) {
            const auto size =
                std::min(static_cast<int32_t>(buffer.len - offset), LZ_decompress_write_size(current->lz_decoder));
            if (size > 0) {
                if (LZ_decompress_write(current->lz_decoder, reinterpret_cast<uint8_t*>(buffer.buf) + offset, size)
                    != size) {
                    throw_lz_error(current->lz_decoder);
                    throw std::runtime_error("the LZ decoder did not consume all the bytes");
                }
            }
            decoder_consume_all(current);
            offset += size;
        }
        PyEval_RestoreThread(thread_state);
        PyBuffer_Release(&buffer);
        return full_packets_bytes(current);
    } catch (const std::exception& exception) {
        PyEval_RestoreThread(thread_state);
        PyBuffer_Release(&buffer);
        PyErr_SetString(PyExc_RuntimeError, exception.what());
    }
    return nullptr;
}
static PyObject* decoder_finish(PyObject* self, PyObject*) {
    auto thread_state = PyEval_SaveThread();
    auto current = reinterpret_cast<decoder*>(self);
    try {
        if (!current->lz_decoder) {
            throw std::runtime_error("finish called twice");
        }
        if (LZ_decompress_finish(current->lz_decoder) < 0) {
            throw_lz_error(current->lz_decoder);
        }
        decoder_consume_all(current);
        PyEval_RestoreThread(thread_state);
        auto result = PyTuple_New(2);
        PyTuple_SET_ITEM(result, 0, full_packets_bytes(current));
        PyTuple_SET_ITEM(
            result,
            1,
            PyBytes_FromStringAndSize(
                reinterpret_cast<const char*>(current->decoded_buffer.data()),
                static_cast<Py_ssize_t>(current->decoded_buffer.size())));
        {
            std::vector<uint8_t> empty;
            current->decoded_buffer.swap(empty);
        }
        LZ_decompress_close(current->lz_decoder);
        current->lz_decoder = nullptr;
        return result;
    } catch (const std::exception& exception) {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_RuntimeError, exception.what());
    }
    return nullptr;
}
static PyMethodDef decoder_methods[] = {
    {"decompress", decoder_decompress, METH_VARARGS, nullptr},
    {"finish", decoder_finish, METH_NOARGS, nullptr},
    {nullptr, nullptr, 0, nullptr},
};
static int decoder_init(PyObject* self, PyObject* args, PyObject*) {
    uint64_t word_size = 1;
    if (!PyArg_ParseTuple(args, "|K", &word_size)) {
        return -1;
    }
    auto current = reinterpret_cast<decoder*>(self);
    try {
        current->word_size = word_size;
        if (current->word_size == 0) {
            throw std::runtime_error("word_size cannot be zero");
        }
        current->lz_decoder = LZ_decompress_open();
        if (!current->lz_decoder) {
            throw std::runtime_error("the LZ decoder could not be allocated");
        }
        if (LZ_decompress_errno(current->lz_decoder) != LZ_ok) {
            LZ_decompress_close(current->lz_decoder);
            throw std::runtime_error("initializing the LZ decoder failed");
        }
    } catch (const std::exception& exception) {
        PyErr_SetString(PyExc_RuntimeError, exception.what());
        return -1;
    }
    return 0;
}
static PyTypeObject decoder_type = {PyVarObject_HEAD_INIT(nullptr, 0)};

/// encoder compresses Lzip buffers.
struct encoder {
    PyObject_HEAD LZ_Encoder* lz_encoder;
    std::vector<uint8_t> encoded_buffer;
};
void encoder_consume_all(encoder* current) {
    for (;;) {
        const auto previous_size = current->encoded_buffer.size();
        current->encoded_buffer.resize(previous_size + internal_buffer_size);
        const auto total_compressed = LZ_compress_total_in_size(current->lz_encoder);
        const auto encoded_bytes_read =
            LZ_compress_read(current->lz_encoder, current->encoded_buffer.data() + previous_size, internal_buffer_size);
        if (encoded_bytes_read < 0) {
            current->encoded_buffer.resize(previous_size);
            throw_lz_error(current->lz_encoder);
        }
        if (encoded_bytes_read == 0) {
            current->encoded_buffer.resize(previous_size);
            if (LZ_compress_total_in_size(current->lz_encoder) == total_compressed) {
                break;
            }
            continue;
        }
        current->encoded_buffer.resize(previous_size + encoded_bytes_read);
    }
}
static void encoder_dealloc(PyObject* self) {
    auto current = reinterpret_cast<encoder*>(self);
    {
        std::vector<uint8_t> empty;
        current->encoded_buffer.swap(empty);
    }
    if (current->lz_encoder) {
        LZ_compress_close(current->lz_encoder);
        current->lz_encoder = nullptr;
    }
    Py_TYPE(self)->tp_free(self);
}
static PyObject* encoder_new(PyTypeObject* type, PyObject*, PyObject*) {
    return type->tp_alloc(type, 0);
}
static PyMemberDef encoder_members[] = {
    {nullptr, 0, 0, 0, nullptr},
};
static PyObject* encoder_compress(PyObject* self, PyObject* args) {
    Py_buffer buffer;
    if (!PyArg_ParseTuple(args, "y*", &buffer)) {
        return nullptr;
    }
    auto thread_state = PyEval_SaveThread();
    auto current = reinterpret_cast<encoder*>(self);
    try {
        if (!current->lz_encoder) {
            throw std::runtime_error("compress cannot be called after finish");
        }
        for (Py_ssize_t offset = 0; offset < buffer.len;) {
            const auto size =
                std::min(static_cast<int32_t>(buffer.len - offset), LZ_compress_write_size(current->lz_encoder));
            if (size > 0) {
                if (LZ_compress_write(current->lz_encoder, reinterpret_cast<uint8_t*>(buffer.buf) + offset, size)
                    != size) {
                    throw_lz_error(current->lz_encoder);
                    throw std::runtime_error("the LZ encoder did not consume all the bytes");
                }
            }
            encoder_consume_all(current);
            offset += size;
        }
        PyEval_RestoreThread(thread_state);
        PyBuffer_Release(&buffer);
        auto result = PyBytes_FromStringAndSize(
            reinterpret_cast<const char*>(current->encoded_buffer.data()),
            static_cast<Py_ssize_t>(current->encoded_buffer.size()));
        current->encoded_buffer.clear();
        return result;
    } catch (const std::exception& exception) {
        PyEval_RestoreThread(thread_state);
        PyBuffer_Release(&buffer);
        PyErr_SetString(PyExc_RuntimeError, exception.what());
    }
    return nullptr;
}
static PyObject* encoder_finish(PyObject* self, PyObject*) {
    auto current = reinterpret_cast<encoder*>(self);
    auto thread_state = PyEval_SaveThread();
    try {
        if (!current->lz_encoder) {
            throw std::runtime_error("finish called twice");
        }
        if (LZ_compress_finish(current->lz_encoder) < 0) {
            throw_lz_error(current->lz_encoder);
        }
        encoder_consume_all(current);
        PyEval_RestoreThread(thread_state);
        auto result = PyBytes_FromStringAndSize(
            reinterpret_cast<const char*>(current->encoded_buffer.data()),
            static_cast<Py_ssize_t>(current->encoded_buffer.size()));
        {
            std::vector<uint8_t> empty;
            current->encoded_buffer.swap(empty);
        }
        LZ_compress_close(current->lz_encoder);
        current->lz_encoder = nullptr;
        return result;
    } catch (const std::exception& exception) {
        PyEval_RestoreThread(thread_state);
        PyErr_SetString(PyExc_RuntimeError, exception.what());
    }
    return nullptr;
}
static PyMethodDef encoder_methods[] = {
    {"compress", encoder_compress, METH_VARARGS, nullptr},
    {"finish", encoder_finish, METH_NOARGS, nullptr},
    {nullptr, nullptr, 0, nullptr},
};
static int encoder_init(PyObject* self, PyObject* args, PyObject*) {
    int32_t dictionary_size = 1 << 23;
    int32_t match_len_limit = 36;
    uint64_t member_size = 1ull << 51;
    if (!PyArg_ParseTuple(args, "|iiK", &dictionary_size, &match_len_limit, &member_size)) {
        return -1;
    }
    auto current = reinterpret_cast<encoder*>(self);
    try {
        current->lz_encoder = LZ_compress_open(dictionary_size, match_len_limit, member_size);
        if (!current->lz_encoder) {
            throw std::runtime_error("the LZ encoder could not be allocated");
        }
        if (LZ_compress_errno(current->lz_encoder) != LZ_ok) {
            LZ_compress_close(current->lz_encoder);
            throw std::runtime_error("initializing the LZ encoder failed");
        }
    } catch (const std::exception& exception) {
        PyErr_SetString(PyExc_RuntimeError, exception.what());
        return -1;
    }
    return 0;
}
static PyTypeObject encoder_type = {PyVarObject_HEAD_INIT(nullptr, 0)};

static PyMethodDef lzip_extension_methods[] = {{nullptr, nullptr, 0, nullptr}};
static struct PyModuleDef lzip_extension_definition = {
    PyModuleDef_HEAD_INIT,
    "lzip_extension",
    "lzip compresses and decompresses .lz archives",
    -1,
    lzip_extension_methods};
PyMODINIT_FUNC PyInit_lzip_extension() {
    auto module = PyModule_Create(&lzip_extension_definition);
    decoder_type.tp_name = "lzip_extension.Decoder";
    decoder_type.tp_basicsize = sizeof(decoder);
    decoder_type.tp_dealloc = decoder_dealloc;
    decoder_type.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
    decoder_type.tp_methods = decoder_methods;
    decoder_type.tp_members = decoder_members;
    decoder_type.tp_new = decoder_new;
    decoder_type.tp_init = decoder_init;
    PyType_Ready(&decoder_type);
    PyModule_AddObject(module, "Decoder", (PyObject*)&decoder_type);
    encoder_type.tp_name = "lzip_extension.Encoder";
    encoder_type.tp_basicsize = sizeof(encoder);
    encoder_type.tp_dealloc = encoder_dealloc;
    encoder_type.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
    encoder_type.tp_methods = encoder_methods;
    encoder_type.tp_members = encoder_members;
    encoder_type.tp_new = encoder_new;
    encoder_type.tp_init = encoder_init;
    PyType_Ready(&encoder_type);
    PyModule_AddObject(module, "Encoder", (PyObject*)&encoder_type);
    return module;
}
