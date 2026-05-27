import struct



class BLKTypes:
    """
    A class that is construction with the name_map and parameter data
    inputs:
    typeId: a single byte (as int) that represents the type ID, must match types as shown below
    data: 4 bytes (as bytes) that is the raw data being parsed based on typeId
    returns:
    a parsed datatype
    string, int, int[], long, float, float[], bool, color

    one note: this code was mostly generated using chat-gpt. it was made using gpt to javascript (a script one of my friends made)
    then translated to python using gpt again. I actually made my own version of this. but this is SOMEHOW much faster and it angers me deeply
    """
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

    @staticmethod
    def bytesToInt(bytes_data):
        if len(bytes_data) < 4:
            return None
        return struct.unpack('<i', bytes_data[:4])[0]

    @staticmethod
    def bytesToUInt(bytes_data):
        if len(bytes_data) < 4:
            return None
        return struct.unpack('<I', bytes_data[:4])[0]

    @staticmethod
    def bytesToFloat(bytes_data):
        if len(bytes_data) < 4:
            return None
        return struct.unpack('<f', bytes_data[:4])[0]

    @staticmethod
    def bytesToLong(bytes_data):
        if len(bytes_data) < 8:
            return None
        return struct.unpack('<q', bytes_data[:8])[0]

    @staticmethod
    def bytesToOffset(bytes_data):
        return BLKTypes.bytesToUInt(bytes_data)

    @staticmethod
    def extractString(data, offset):
        try:
            nullIndex = data.index(b'\x00', offset)
        except ValueError:
            nullIndex = len(data)
        end = nullIndex
        return data[offset:end].decode('utf-8', errors="ignore")

    def __init__(self, name_map, param_data):
        self.name_map = name_map
        self.param_data = param_data

    def fromRawParamInfo(self, typeId, data):
        if typeId == self.STRING:
            offset = self.bytesToUInt(data)
            if offset is None:
                return None

            in_name_map = (offset >> 31) == 1
            actualOffset = offset & 0x7FFFFFFF

            if in_name_map:
                return self.name_map[actualOffset] if actualOffset < len(self.name_map) else None
            else:
                return self.extractString(self.param_data, actualOffset)
        elif typeId == self.INT:
            return self.bytesToInt(data)
        elif typeId == self.FLOAT:
            return self.bytesToFloat(data)
        elif typeId == self.FLOAT2:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 8 > len(self.param_data):
                return None
            return [
                self.bytesToFloat(self.param_data[offset:offset + 4]),
                self.bytesToFloat(self.param_data[offset + 4:offset + 8])
            ]
        elif typeId == self.FLOAT3:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 12 > len(self.param_data):
                return None
            return [
                self.bytesToFloat(self.param_data[offset:offset + 4]),
                self.bytesToFloat(self.param_data[offset + 4:offset + 8]),
                self.bytesToFloat(self.param_data[offset + 8:offset + 12])
            ]
        elif typeId == self.FLOAT4:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 16 > len(self.param_data):
                return None
            return [
                self.bytesToFloat(self.param_data[offset:offset + 4]),
                self.bytesToFloat(self.param_data[offset + 4:offset + 8]),
                self.bytesToFloat(self.param_data[offset + 8:offset + 12]),
                self.bytesToFloat(self.param_data[offset + 12:offset + 16])
            ]
        elif typeId == self.INT2:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 8 > len(self.param_data):
                return None
            return [
                self.bytesToInt(self.param_data[offset:offset + 4]),
                self.bytesToInt(self.param_data[offset + 4:offset + 8])
            ]
        elif typeId == self.INT3:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 12 > len(self.param_data):
                return None
            return [
                self.bytesToInt(self.param_data[offset:offset + 4]),
                self.bytesToInt(self.param_data[offset + 4:offset + 8]),
                self.bytesToInt(self.param_data[offset + 8:offset + 12])
            ]
        elif typeId == self.BOOL:
            return data[0] != 0
        elif typeId == self.COLOR:
            return [
                data[0],
                data[1],
                data[2],
                data[3],
            ]
        elif typeId == self.FLOAT12:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 48 > len(self.param_data):
                return None
            result = []
            for i in range(12):
                start = offset + i * 4
                end = start + 4
                result.append(self.bytesToFloat(self.param_data[start:end]))
            return result
        elif typeId == self.LONG:
            offset = self.bytesToOffset(data)
            if offset is None or offset + 8 > len(self.param_data):
                return None
            return self.bytesToLong(self.param_data[offset:offset + 8])
        else:
            return None
