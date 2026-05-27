import io
import copy
import math


class DataHandler:
    """
    DataHandler handles all data that will be used by the decoder. can be passed either a blob of data (raw hex) or a file
    stream. The functions of the class will handle all grabbing of data and movement of pointer.
    data: can either be a blob of data (raw hex) or a file object gotten from open()
    offset: specifies when in the data to set the pointer
    read_from_start: a boolean that only applies to files, specifies whether to start at the beginning of the file when
    doing file io. if there is a set offset, it goes to the start of the file, then applies the offset

    most common use case is to pass a 'bytes' or 'bytearray' object

    current usage inside the project is only as passing raw data and not using file io
    """

    def __init__(self, data, offset: int, read_from_start: bool):
        self._data = data
        self._ptr = offset  # only used when blob
        self._isFile = False
        if type(data) is io.BufferedReader:
            self._isFile = True
            if read_from_start:
                data.seek(offset)
            else:
                data.read(offset)
        else:
            self.length = len(self._data)


    '''
    fetches (count) number of bytes from the data source
    '''

    def fetch(self, count: int) -> bytes:
        if self._isFile:
            return self._data.read(count)
        self._ptr += count
        return self._data[self._ptr - count:self._ptr]

    '''
    advances (count) number of bytes from the data source, unlike fetch, it discards any collected data
    '''

    def advance(self, count: int) -> None:
        if self._isFile:
            self._data.read(count)
            return
        self._ptr += count
        return

    def get_rest(self):
        if self._isFile:
            return self._data.read()
        return self._data[self._ptr:]

    def get_ptr(self):
        return copy.deepcopy(self._ptr)

    '''
    function to get next four bytes from the data source and convert it to an int
    '''
    def get_int(self):
        raw = self.fetch(4)
        return int.from_bytes(raw, 'little')

    def get_long(self):
        raw = self.fetch(8)
        return int.from_bytes(raw, 'little')

    def decode_uleb128(self):
        """Decodes a ULEB128 encoded value."""
        value = 0
        shift = 0
        while True:
            byte = self.fetch(1)[0]
            value |= (byte & 0x7f) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return value

    def is_EOF(self):
        if not self._isFile:
            return self._ptr == self.length

    def readString(self):
        payload = b""
        c = self.fetch(1)
        while c != b"\x00":
            payload += c
            c = self.fetch(1)
        return payload


class BitStream:
    def __init__(self, data, bit_index=0, do_im_hex=False):
        self.data = data
        self.current_bit_index = bit_index
        self.do_im_hex = do_im_hex
        self.count = 0

    def fetch(self, bit_count, desc="_") -> bytes:

        if self.do_im_hex:
            add = 0 if self.current_bit_index % 8 == 0 or bit_count == 0 else 1
            print(f"u8 {desc}_{self.current_bit_index}[{math.ceil(bit_count/8)+add}] @ {self.current_bit_index//8};")
        if bit_count % 8 == 0 and bit_count > 0 and self.current_bit_index % 8 == 0:
            out = self.data[self.current_bit_index//8:self.current_bit_index//8+bit_count//8]
            self.current_bit_index += bit_count
            return out


        out_buff = bytearray(math.ceil(bit_count / 8))
        write_bit = 0
        for i in range(bit_count):
            current_index = self.current_bit_index // 8 # gets the floor to get the rounded down byte index
            if current_index >= len(self.data):
                break
            temp_bit = (self.data[current_index] & (2**(7-self.current_bit_index%8))) != 0 # gets the next bit in line to be read
            if temp_bit:
                out_buff[write_bit // 8] |= (2**(7-write_bit%8))
            write_bit += 1
            # print(self.data[current_index] & (2**(self.current_bit_index%8)))
            # print(hex(self.data[current_index]), bin(self.data[current_index]), bin((2**(7-write_bit%8))), write_bit)
            self.current_bit_index += 1
        # print("last index: ", write_bit)
        if len(out_buff) > 0 and write_bit % 8 != 0:
            out_buff[math.ceil(bit_count / 8)-1] = out_buff[math.ceil(bit_count / 8)-1] >>(8-write_bit % 8)
        return out_buff

    def advance(self, bit_count, desc="_") -> None:
        if self.do_im_hex:
            add = 0 if self.current_bit_index % 8 == 0 or bit_count == 0 else 1
            print(f"u8 {desc}_{self.current_bit_index}[{math.ceil(bit_count/8)+add}] @ {self.current_bit_index//8};")
        self.current_bit_index += bit_count

    def get_int(self, desc="_"):
        if self.do_im_hex:
            add = 0 if self.current_bit_index % 8 == 0 else 1
            print(f"u8 {desc}_{self.current_bit_index}[{4+add}] @ {self.current_bit_index//8};")
        raw = self.fetch(4*8)
        return int.from_bytes(raw, 'little')

    def get_long(self, desc="_"):
        if self.do_im_hex:
            add = 0 if self.current_bit_index % 8 == 0 else 1
            print(f"u8 {desc}_{self.current_bit_index}[{8+add}] @ {self.current_bit_index//8};")
        raw = self.fetch(8*8)
        return int.from_bytes(raw, 'little')

    def decode_uleb128(self, desc="_"):
        """Decodes a ULEB128 encoded value."""
        value = 0
        shift = 0
        while True:
            byte = self.fetch(8, desc=f"ULEB{desc}")[0]
            value |= (byte & 0x7f) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return value

    def get_rest(self, desc="_"):
        EOL_length = len(self.data)-self.current_bit_index // 8 # gets the floor to get the rounded down byte index
        return self.fetch(EOL_length*8, desc=desc)

    def is_EOF(self):
        if self.current_bit_index >> 3 > len(self.data):
            return True
        return False