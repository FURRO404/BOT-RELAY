import zstandard as zstd
from DAGOR_FILES.WtFileUtils.BitStream import BitStream

"""
this file only exists because zstandard doesnt give you an easy way to see the entire size of a zstd block, so I made one
"""


class _Frame:
    def __init__(self, bs: BitStream):
        if bs.ReadU32("ZSTD_Magic") != 0xFD2FB528:
            raise Exception("Invalid Magic")
        flags = bs.ReadU8("ZSTD_Flags")
        self.Frame_Content_Size_flag = flags >> 6  # (flags & 0b11000000)
        self.Single_Segment_flag = (flags & 0b100000) >> 5
        self.Unused_bit = (flags & 0b10000) >> 4
        self.Reserved_bit = (flags & 0b1000) >> 3
        self.Content_Checksum_flag = (flags & 0b100) >> 2
        self.Dictionary_ID_flag = flags & 0b11

        self.FCS_Field_Size = 2 ** self.Frame_Content_Size_flag
        if self.FCS_Field_Size == 1 and self.Single_Segment_flag == 0:
            self.FCS_Field_Size = 0

        self.DID_Field_Size = self.Dictionary_ID_flag
        if self.Single_Segment_flag == 0:
            self.Window_Descriptor = bs.ReadU8("ZSTD_Windows_Descriptor")

        self.Dictionary_ID = bs.ReadBytes(self.DID_Field_Size, "ZSTD_Dictionary_ID")

        self.Frame_Content_Size = bs.ReadBytes(self.FCS_Field_Size, "ZSTD_Frame_Content_Size")
        # print(self.Frame_Content_Size_flag)
        # print(self.Single_Segment_flag)
        # print(self.Unused_bit)
        # print(self.Reserved_bit)
        # print(self.Content_Checksum_flag)
        # print(self.Dictionary_ID_flag)


class _Blocks:
    def __init__(self, frame, bs: BitStream):
        self.block_count = 0
        self.blocks = []
        self.frame: _Frame = frame
        self.read_blocks(bs)
        if self.frame.Content_Checksum_flag == 1:
            bs.ReadU32("Zstd_Checksum")
        bs.Flush()

    def read_blocks(self, bs: BitStream):
        Last_Block = 0
        while Last_Block == 0:
            Block_Header = bs.ReadBitsInt(24, "ZSTD_Block_Header")
            Last_Block = Block_Header & 0b1
            Block_Type = (Block_Header & 0b110) >> 1
            block_size = Block_Header >> 3
            bs.IgnoreBytes(block_size)
            # print(Last_Block, Block_Type, block_size)


class ZstdContent:
    def __init__(self, bs: BitStream):
        self.bs = bs
        self.start = bs.GetReadOffset()
        self.frm = _Frame(bs)
        self.blocks = _Blocks(self.frm, bs)
        self.end = bs.GetReadOffset()

    def decompress(self):
        self.bs.SetReadOffset(self.start)
        return zstd.decompress(self.bs.ReadBits(self.end - self.start))
