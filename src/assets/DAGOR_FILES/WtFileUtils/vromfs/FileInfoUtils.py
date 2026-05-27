from ..Exceptions import VROMFSException


PlatformType = {
    0x43500000: "Pc",
    0x534F6900: "Ios",
    0x646E6100: "Android"
}

HeaderType = {
    0x73465256: "VRFS",  # base header
    0x78465256: "VRFX",  # extended header
}

class Packing:
    Packing = {
        # ZSTD compressed and obfuscated. No digest
        0x10: "ZSTD_OBFS_NOCHECK",

        # Image in plain form. With digest
        0x20: "PLAIN",

        # Same as ZSTD_OBFS_NOCHECK except with digest
        0x30: "ZSTD_OBFS",
    }

    def __init__(self, packing_raw):
        self.packing_raw = packing_raw
        self.packing = self.Packing.get(packing_raw)
        if packing_raw is None:
            raise VROMFSException("Invalid packing type")

    def has_digest(self):
        return self.packing_raw != 0x10

    def has_zstd_obfs(self):
        return self.packing_raw != 0x20

class Version:
    def __init__(self, data):
        self.global_ = None
        self.major = None
        self.minor = None
        self.patch = None
        if type(data) in [bytes, bytearray]:
            self.global_ = data[3]
            self.major = data[2]
            self.minor = data[1]
            self.patch = data[0]
        elif type(data) == str:
            pass