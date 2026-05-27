import struct

types = {
    0x01: "STRING",
    0x02: "INT",
    0x07: "INT2",
    0x08: "INT3",
    0x0C: "LONG",
    0x03: "FLOAT",
    0x04: "FLOAT2",
    0x05: "FLOAT3",
    0x06: "FLOAT4",
    0x0B: "FLOAT12",
    0x09: "BOOL",
    0x0A: "COLOR"
}

'''
this functions the exact same as ParamParser.py, but its the deprecated one mentioned in the notes.
'''
class BlkTypes:
    STRING = 0x01
    INT = 0x02
    INT2 = 0x07
    INT3 = 0x08
    LONG = 0x0C
    FLOAT = 0x03
    FLOAT2 = 0x04
    FLOAT3 = 0x05
    FLOAT4 = 0x06
    FLOAT12 = 0x0B
    BOOL = 0x09
    COLOR = 0x0A

    types = {
        0x01: "STRING",
        0x02: "INT",
        0x07: "INT2",
        0x08: "INT3",
        0x0C: "LONG",
        0x03: "FLOAT",
        0x04: "FLOAT2",
        0x05: "FLOAT3",
        0x06: "FLOAT4",
        0x0B: "FLOAT12",
        0x09: "BOOL",
        0x0A: "COLOR"
    }

    def __init__(self, name_map, param_data):
        self.name_map = name_map
        self.param_data = param_data

    def from_raw(self, type_id, data):
        if type_id == self.STRING:
            offset = int.from_bytes(data, 'little')  # turns data into int
            in_name_map = (
                                      offset >> 31) == 1  # forces the most significant bit to be the only possible value in the int
            if in_name_map:
                offset &= 2147483647  # applies a bitmask to remove most significant bit (most far left)
                return "" + self.name_map[offset] + ""
            temp = self.param_data[offset:]
            print(temp)
            return temp[:temp.find(b"\x00")].decode("utf-8")
            # print(hex(offset))
            return in_name_map
        if type_id == self.INT:
            return int.from_bytes(data, 'little')
        if type_id == self.INT2:
            offset = int.from_bytes(data, 'little')
            return [int.from_bytes(self.param_data[offset + i * 4:offset + i * 4 + 4], 'little') for i in range(2)]
        if type_id == self.INT3:
            offset = int.from_bytes(data, 'little')
            return [int.from_bytes(self.param_data[offset + i * 4:offset + i * 4 + 4], 'little') for i in range(3)]
        if type_id == self.LONG:
            offset = int.from_bytes(data, 'little')
            return int.from_bytes(self.param_data[offset:offset + 8], 'little')
            pass
        if type_id == self.FLOAT:
            return struct.unpack("f", data)[0]
        if type_id == self.FLOAT2:
            offset = int.from_bytes(data, 'little')
            return [struct.unpack("f", self.param_data[offset:offset + 4]),
                    struct.unpack("f", self.param_data[offset + 4:offset + 8])]
            pass
        if type_id == self.FLOAT3:
            offset = int.from_bytes(data, 'little')
            return [struct.unpack("f", self.param_data[offset:offset + 4]),
                    struct.unpack("f", self.param_data[offset + 4:offset + 8]),
                    struct.unpack("f", self.param_data[offset + 8:offset + 12])]
            pass
        if type_id == self.FLOAT4:
            offset = int.from_bytes(data, 'little')
            return [struct.unpack("f", self.param_data[offset:offset + 4]),
                    struct.unpack("f", self.param_data[offset + 4:offset + 8]),
                    struct.unpack("f", self.param_data[offset + 8:offset + 12]),
                    struct.unpack("f", self.param_data[offset + 12:offset + 16])]
            pass
        if type_id == self.FLOAT12:
            offset = int.from_bytes(data, 'little')
            print(self.param_data[offset:offset + 64])
            return [struct.unpack("f", self.param_data[offset:offset + 4]),
                    struct.unpack("f", self.param_data[offset + 4:offset + 8]),
                    struct.unpack("f", self.param_data[offset + 8:offset + 12]),
                    struct.unpack("f", self.param_data[offset + 12:offset + 16]),
                    struct.unpack("f", self.param_data[offset + 16:offset + 18]),
                    struct.unpack("f", self.param_data[offset + 18:offset + 24]),
                    struct.unpack("f", self.param_data[offset + 24:offset + 32]),
                    struct.unpack("f", self.param_data[offset + 32:offset + 48]),
                    struct.unpack("f", self.param_data[offset + 48:offset + 52]),
                    struct.unpack("f", self.param_data[offset + 52:offset + 56]),
                    struct.unpack("f", self.param_data[offset + 56:offset + 60]),
                    struct.unpack("f", self.param_data[offset + 60:offset + 64])]
            pass
        if type_id == self.BOOL:
            return int.from_bytes(data, 'little') == 1
        if type_id == self.COLOR:
            print(f"COLOR: {data}")
            return ("_COLOR_")