class FileType:
    """
    Helper Class
    When provided the first byte from a blk file, provides info about that blk type

    (basically ripped off from flare flo's rust parser, look at README for more info)
    """
    types = {
        0x00: "BBF",  # unknown
        0x01: "FAT",  # BLK file with name map builtin
        0x02: "FAT_ZSTD",  # FAT but ZSTD compressed
        0x03: "SLIM",  # name map stored externally, needs to be supplied
        0x04: "SLIM_ZSTD",  # Same as slim but zstd compressed
        0x05: "SLIM_ZSTD_DICT",  # Same as SLIM_ZSTD, but with an external ZSTD Dict
    }

    def __init__(self, byte_):
        self.type_byte = byte_
        self.type_name = self.types[byte_]

    def is_slim(self):
        return self.type_byte in [0x03, 0x04, 0x05]

    def is_zstd(self):
        return self.type_byte in [0x02, 0x04, 0x05]

    def needs_dict(self):
        return self.type_byte == 0x05
