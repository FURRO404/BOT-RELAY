import os
import zstandard as zstd
import _md5
import traceback
from itertools import islice


from ..DataHandler import DataHandler
from ..vromfs.FileInfoUtils import HeaderType, PlatformType, Packing, Version
from ..Exceptions import VROMFSException
from ..FileSystem.FSDirectory import FSDirectory
from ..FileSystem.File import VROMFs_File
from ..FileSystem.FileSystemQuery import FileSystemQuery
from ..blk.BlkParser import BlkDecoder

ZSTD_XOR_PATTERN = [0xAA55AA55, 0xF00FF00F, 0xAA55AA55, 0x12481248]
ZSTD_XOR_PATTERN_REV = ZSTD_XOR_PATTERN[::-1]

def batched(iterable, n, *, strict=False):
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError('n must be at least one')
    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        if strict and len(batch) != n:
            raise ValueError('batched(): incomplete batch')
        yield batch

class VROMFs:
    """
    A VROMFs unpacker
    given a path to a vromfs file, will extract basic metadata of the file
    certain methods will fetch all the data from the vromfs file
    this includes
    """

    def __init__(self, path):
        if not os.path.exists(path):
            raise VROMFSException("Bad file path")
        self._raw: _RawData = None
        self.path = path
        self._header = None
        self._internal_parsed = False
        self._name_map = None
        self._has_zstd_dict = False
        self._zstd_dict = None
        self.version: VROMFs_File = None  # A VROMFs_File

    def get_directory(self, files=None, directory=None) -> FSDirectory:
        """
        Creates a Directory Object containing all the files in the VROMFs. as an optimization method, you can pass
        a list of files you may have extracted manually, same is for the directory
        """
        if directory is None:
            directory = FSDirectory("base", None)
        if files is None:
            files = self._get_file_data()
        for f in files:
            query = FileSystemQuery(f.true_name, file_obj=f)

            directory.add_file(query)
        return directory

    def get_files(self):
        return self._get_file_data()
        """
        Will fetch all the files from the directory

        :return:
        returns them as a list of File Objects
        """

    def _get_file_data(self, generate_files=True):
        """
        internal function to get all files in a vromf file
        sets self._internal_parsed to True
        sets _name_map
        sets _zstd_dict
        """
        if self._raw is None:
            self._raw = _RawData(self.path)
        data = DataHandler(self._raw.inner_data, 0, False)
        has_digest = False  # currently not used, its truthiness is still calculated
        names_header = data.fetch(4)
        match (names_header[0]):
            case 0x20:
                has_digest = False
            case 0x30:
                has_digest = True
            case _:
                pass
                #raise VROMFSException("Bad file type")
        names_offset = int.from_bytes(names_header, byteorder='little')
        names_count = data.get_int()
        data.advance(8)  # advances a u64

        data_info_offset = data.get_int()
        data_info_count = data.get_int()
        data.advance(8)
        if has_digest:
            pass  # not implemented

        name_info_len = names_count * 8
        name_info = self._raw.inner_data[names_offset:names_offset + name_info_len]
        name_info_chunks = [name_info[x:x + 8] for x in range(0, len(name_info), 8)]
        parsed_names_offsets = [int.from_bytes(x, byteorder="little") for x in name_info_chunks]
        names = [b"" for _ in range(names_count)]
        for index, offset in enumerate(parsed_names_offsets):
            chars = []
            while self._raw.inner_data[offset] != 0:
                chars.append(self._raw.inner_data[offset])
                offset += 1
            names[index] = bytes(chars)

        data_info_len = data_info_count * 4 * 4  # a len(u32) * 4
        data_info = self._raw.inner_data[data_info_offset:data_info_offset + data_info_len]
        data_info_split = [data_info[x:x + 4] for x in range(0, len(data_info), 4)]
        data_info_split_quad = batched(data_info_split, 4)
        countz = 0
        file_list = []
        for b1, b2, *_ in data_info_split_quad:
            offset, size = int.from_bytes(b1, byteorder="little"), int.from_bytes(b2, byteorder="little")
            if names[countz] == b"\xff?nm":
                names[countz] = b"nm"
                raw = self._raw.inner_data[offset:offset + size]
                _names_digest = raw[0:8]
                _dict_digest = raw[8:40]
                zstd_data = raw[40:]
                raw_nm = DataHandler(zstd.decompress(zstd_data), 0, False)
                names_count = raw_nm.decode_uleb128()
                names_data_size = raw_nm.decode_uleb128()

                names = raw_nm.fetch(names_data_size).split(b"\x00")[:-1]
                if len(names) != names_count:
                    raise VROMFSException("Bad Name Map")
                self._name_map = names
            elif names[countz].endswith(b"dict"):
                self._has_zstd_dict = True
                self._zstd_dict = zstd.ZstdCompressionDict(self._raw.inner_data[offset:offset + size])

            elif names[countz] == b"version":
                self.version = VROMFs_File(names[countz].decode("utf-8").split("/"), offset, size, self)
                pass  # implement doing stuff with this and metadata file
            elif generate_files:  # this code body handles all file creation as it only includes important files
                file_list.append(VROMFs_File(names[countz].decode("utf-8").split("/"), offset, size, self))
            countz += 1
        self._internal_parsed = True
        if generate_files:
            return file_list

    '''
    given a VROMFs_File object, will look up that object in the VROMFs and return the unpacked data
    '''

    def open_file(self, file: VROMFs_File):
        if file.VROMFs != self:
            raise VROMFSException("VROMFs called to open file not same as object that generate the File")
        if not self._internal_parsed:
            self._get_file_data(generate_files=False)
        else:
            raw = self._raw.inner_data[file.offset:file.offset + file.size]
            file_type = file.file_name.split(".")[-1]
            data = None
            match file_type:
                case "blk":
                    try:
                        data = BlkDecoder(raw, name_map=self._name_map, zstd_dict=self._zstd_dict).to_dict()
                    except Exception:
                        stack_trace = traceback.format_exc()
                        print(f"blk read error on {file.file_name}, name_map: {self._name_map is not None}, zstd_dict: {self._zstd_dict is not None}")
                        print(stack_trace)
                        data = self.open_file_raw(file)

                case _:
                    data = raw

            return data

    def open_file_raw(self, file: VROMFs_File):
        if self._internal_parsed:
            return self._raw.inner_data[file.offset:file.offset + file.size]
        else:
            self._get_file_data(generate_files=False)

    def _dump_internal(self, path):
        pass


class _RawData:
    size_mask = 0b0000001111111111111111111111111
    """
    given a path, will open the file and do basic parsing and data extraction
    created as a class to allows for helper functions
    """

    def __init__(self, path):
        self.metaData = None
        with open(path, 'rb') as f:
            raw = DataHandler(bytearray(f.read()), 0, False)
        self.inner_data = self._get_inner(raw)

    '''
    returns the inner data
    '''

    def _get_inner(self, raw: DataHandler):
        header_type = HeaderType[raw.get_int()]
        platform = PlatformType[raw.get_int()]
        file_size_before_compression = raw.get_int()
        pack_raw = raw.get_int()
        packing = Packing(pack_raw >> 26)  # the first 6 bits (far left) determine packing info
        pack_size = pack_raw & self.size_mask  # last 26 bits

        inner_data = None
        if header_type == "VRFX":
            raw.advance(4)
            version = Version(raw.fetch(4))
            if pack_size == 0:
                inner_data = raw.get_rest()
            else:
                inner_data = raw.fetch(pack_size)
        else:
            if packing.has_zstd_obfs():  # compressed types only
                inner_data = raw.fetch(pack_size)
            else:
                inner_data = raw.fetch(file_size_before_compression)

        if not packing.has_zstd_obfs():
            return inner_data

        output = zstd.decompress(self.deobfuscate(inner_data))  # every zstd packed type is also obfuscated

        if packing.has_digest():  # checking for hash
            h = raw.fetch(16)
            hash_calc = _md5.md5(output).digest()
            if hash_calc != h:
                raise VROMFSException("Invalid MD5 hash")

        return output

    def get_inner(self):
        return self.inner_data

    @staticmethod
    def deobfuscate(data: bytes):
        lenz = len(data)
        if lenz < 16:
            return data
        elif 32 >= lenz >= 16:
            return _RawData.xor_at_with(data, ZSTD_XOR_PATTERN)  # can cause a crash but I do not give a shit right now
        else:
            start = _RawData.xor_at_with(data, ZSTD_XOR_PATTERN)
            mid_val = (len(data) & 0x03Ff_FFFC) - 16
            other_place = _RawData.xor_at_with(data[mid_val:], ZSTD_XOR_PATTERN_REV)
            return start + data[len(start):mid_val] + other_place + data[mid_val + len(other_place):]

    @staticmethod
    def xor_at_with(data: bytes, xor_key):
        output = b""
        for i in range(4):
            output += (int.from_bytes(data[i * 4:i * 4 + 4], byteorder="little") ^ xor_key[i]).to_bytes(4,
                                                                                                        byteorder='little')
        return output

    def fetch(self):
        pass
