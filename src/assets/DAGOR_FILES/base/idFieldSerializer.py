import sys


from DAGOR_FILES.WtFileUtils.BitStream import BitStream

uint8_t = int
uint16_t = int
uint32_t = int
uint64_t = int
BitSize_t = uint32_t



def pop_count(n):
    count = 0
    while n:
        count += n & 1
        n >>= 1
    return count


def BITS_TO_BYTES(x):
    return (x + 7) >> 3


def BITS_TO_BYTES_WORD_ALIGNED(x):
    return ((x + 31) >> 5) << 2


def BYTES_TO_BITS(x):
    return x << 3


def readSize(from_: BitStream):
    hdr = from_.ReadBitsInt(3, "Serializer_hdr")
    if hdr is None:
        return 0
    match hdr:
        case 1:
            return 1  # 1 bit
        case 2:
            return 8  # 1 byte
        case 3:
            return 16  # 2 bytes
        case 4:
            return 32  # 4 bytes
        case 5:
            return 64  # 8 bytes
        case 6:
            return 96  # 12 bytes
        case 7:
            return 128  # 16 bytes

    assert hdr == 0

    sizeInBits = from_.ReadUleb("Serializer_sizeInBits")
    if sizeInBits is None:
        return 0
    return sizeInBits


class IdFieldSerializer32:
    MAX_FIELDS_NUM: uint8_t = 32

    def __init__(self):
        self.sizes = [0] * self.MAX_FIELDS_NUM
        self.currWrSz = 0
        self.currRdSz = 0

    def setFieldSize(self, sz: uint32_t):
        assert self.currWrSz < self.MAX_FIELDS_NUM
        self.sizes[self.currWrSz] = sz
        self.currWrSz += 1

    def checkFieldSize(self, index: uint8_t, sz: BitSize_t):
        assert index < self.currRdSz
        assert sz == self.sizes[index]

    def writeFieldSize(self, to: BitStream):
        pass

    def readFieldsSizeAndFlag(self, from_: BitStream):
        # fields: uint32_t = 0
        # offset: uint16_t = 0
        start: BitSize_t = from_.GetReadOffset()
        assert start & 7 == 0
        offset = from_.ReadU16("Serializer32_offset")

        fields: uint32_t = from_.ReadUleb("Serializer32_fields")
        startBody = from_.GetReadOffset()
        from_.SetReadOffset((offset << 3) + start)
        self.currRdSz = pop_count(fields)
        for j in range(self.currRdSz):
            self.sizes[j] = readSize(from_)
            # print(self.sizes[j])
            assert (self.sizes[j])

        from_.SetReadOffset(startBody)
        return fields

    def skipReadingField(self, index: uint8_t, from_: BitStream):
        from_.SetReadOffset(from_.GetReadOffset() + self.sizes[index])

    def writeFieldsSize(self):
        raise NotImplementedError()


Id = uint16_t
Index = Id


class IdFieldSerializer255:
    BITS_PER_COUNT: uint32_t = 12
    BIT_MASK_COUNT: uint32_t = (1 << BITS_PER_COUNT) - 1
    MAX_FIELDS_NUM: Index = 255

    def __init__(self):
        self.sizes: list[uint32_t] = [uint32_t()] * self.MAX_FIELDS_NUM
        self.indices: list[Id] = [Id()] * self.MAX_FIELDS_NUM
        self.currWrId: Index = 0
        self.currWrSz: Index = 0
        self.currRdSz: Index = 0
        self.bitsPerId: Index = 0

    def reset(self):
        self.sizes: list[uint32_t] = [uint32_t()] * self.MAX_FIELDS_NUM
        self.indices: list[Id] = [Id()] * self.MAX_FIELDS_NUM
        self.currWrId: Index = 0
        self.currWrSz: Index = 0
        self.currRdSz: Index = 0
        self.bitsPerId: Index = 0

    def setFieldId(self, id_: Id):
        assert self.currWrId < self.MAX_FIELDS_NUM
        self.sizes[self.currWrId] = id_
        self.currWrId += 1

    def setFieldSize(self, sz: uint32_t):
        assert self.currWrSz < self.MAX_FIELDS_NUM
        self.sizes[self.currWrSz] = sz
        self.currWrSz += 1

    @staticmethod
    def alingedToByte(count: BitSize_t):
        return count + 8 - (((count - 1) & 7) + 1)

    def getFieldId(self, index: Index) -> Id:
        return self.indices[index]

    def getFieldSize(self, index: Index) -> uint32_t:
        return self.sizes[index]

    def writeFieldsSize(self, to: BitStream, at: BitSize_t = 0) -> None:
        pass

    def readFieldsSizeAndCount(self, from_: BitStream) -> [Index, int]:
        start: BitSize_t = from_.GetReadOffset()
        assert start & 7 == 0 # alligned to byte
        offset = from_.ReadU16("Serializer255_offset")
        count = from_.ReadU16("Serializer255_count")
        if offset is None or count is None:
            assert False
            return False
        startBody: BitSize_t = from_.GetReadOffset()
        from_.SetReadOffset(BYTES_TO_BITS(offset)+start)
        self.currRdSz = count & self.BIT_MASK_COUNT
        self.bitsPerId = count >> self.BITS_PER_COUNT
        assert self.currRdSz
        for i in range(self.currRdSz):
            self.sizes[i] = readSize(from_)
            assert (self.sizes[i])
        from_.SetReadOffset(BYTES_TO_BITS(BITS_TO_BYTES(from_.GetReadOffset())))
        end = from_.GetReadOffset()
        from_.SetReadOffset(startBody)
        return self.currRdSz, end


    def skipReadingField(self, index: Index, from_: BitStream):
        assert index < self.currRdSz
        from_.SetReadOffset(from_.GetReadOffset() + self.sizes[index])

    def writeFieldsIndex(self, to: BitStream, at: BitSize_t = 0):
        pass

    def readFieldsIndex(self, from_: BitStream) -> bool:
        assert self.currRdSz and self.bitsPerId
        startBody: BitSize_t = from_.GetReadOffset()
        # we are at the startBody so reread offset and check count
        # offset: uint16_t = 0
        # count: Index = 0
        rewind: BitSize_t = BYTES_TO_BITS(2+2) # BYTES_TO_BITS(sizeof(offset)) + BYTES_TO_BITS(sizeof(count));
        assert startBody >= rewind
        from_.SetReadOffset(startBody-rewind)
        offset = from_.ReadU16("Serializer255_offset")
        count = from_.ReadU16("Serializer255_count")
        if offset is None or count is None:
            assert False
            return False
        assert count == (self.currRdSz | (self.bitsPerId << self.BITS_PER_COUNT))
        bitsForIndices = self.alingedToByte(self.currRdSz*self.bitsPerId)
        from_.SetReadOffset(startBody-rewind+BYTES_TO_BITS(offset)-bitsForIndices)
        for i in range(self.currRdSz):
            out = from_.ReadBitsInt(self.bitsPerId, "Serializer255_bitsIdread")
            if out is None:
                assert False
                return False
            self.indices[i] = out
        from_.SetReadOffset(startBody)
        return True

if __name__ == '__main__':
    data = b'k\r,p}\x00\x00\x00\x04\x00D\x00\x0b\x00\x00\x00\x00\x00\x1d\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80?\x00\xd2\xdfFfF\xd7Cfg\xe7F\x10ef_2000_block_10\rt1_player12_0\x07custom7\nesp_market\x01\x01\xff\xe0\x1e\x02@\x00\x10\x07\xe0\x00\x10\x17\xe0\x00\x08\x03\xf0\x80\x008\x06\x00\x01\x10\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd8+\x06-countermeasure_split_launcher_jet_maw_bol_pod\x00R\x00-countermeasure_split_launcher_jet_maw_bol_pod"maw_countermeasures_launcher_chaffN\x00+countermeasure_large_split_launcher_jet_maw\x00\x10\x00+countermeasure_large_split_launcher_jet_maw(maw_countermeasures_launcher_chaff_large\x10\x00\x13cannon_mauser_bk_27\x00\x96\x00\x00\x00\x00\x00\x10"maw_countermeasures_launcher_chaff(maw_countermeasures_launcher_chaff_large+MAW_system_heli_false_thermal_targets_large\x0bf_4c_g_suit\x10air_extinguisher\x0fbk_27_belt_pack\x13gr_litening_iii_pod\ruk_paveway_iv\tus_gbu_48\x0fuk_brimstone_dm\x0eus_1000lb_mk83\tus_gbu54b\x0eus_2000lb_mk84\tus_aim_9l\tus_aim_9m\x0bus_aim_120b\x08\x12new_compressor_jet\x0fhydravlic_power\x05cd_98\nhp_105_jet\x0ff_4c_CdMin_Fuse\rstructure_str\tnew_cover\rbk_27_new_gun\x9f\x0c\x01;\xbc\x06skin_condition\x00camo_scale\x00camo_rotation\x00decal0Line0\x00decal0Line1\x00decal0Line2\x00decal0Line3\x00decal0HaveCP\x00decal0CPNormDepth\x00decal0CPNormDepth1\x00decal0RotScale\x00decal0Mirrored\x00decal0Wrap\x00decal0Abs\x00decal0OppositeMirrored\x00decal0WidthBox\x00decal0Tex\x00decal1Line0\x00decal1Line1\x00decal1Line2\x00decal1Line3\x00decal1HaveCP\x00decal1CPNormDepth\x00decal1CPNormDepth1\x00decal1RotScale\x00decal1Mirrored\x00decal1Wrap\x00decal1Abs\x00decal1OppositeMirrored\x00decal1WidthBox\x00decal1Tex\x00decal2Line0\x00decal2Line1\x00decal2Line2\x00decal2Line3\x00decal2HaveCP\x00decal2CPNormDepth\x00decal2CPNormDepth1\x00decal2RotScale\x00decal2Mirrored\x00decal2Wrap\x00decal2Abs\x00decal2OppositeMirrored\x00decal2WidthBox\x00decal2Tex\x00decal3Line0\x00decal3Line1\x00decal3Line2\x00decal3Line3\x00decal3HaveCP\x00decal3CPNormDepth\x00decal3CPNormDepth1\x00decal3RotScale\x00decal3Mirrored\x00decal3Wrap\x00decal3Abs\x00decal3OppositeMirrored\x00decal3WidthBox\x00decal3Tex\x00\x01;\x80\x02\x00steamysnuggler_decal\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xdb\x0f\xc9?\x00\x00\x80?\x1074\xbc\x00\x00\x00\x00\xe0\x92\xaa\xbe}\x10\xe9\xbe\xe0\x92\xaa\xbe\x00\x00\x00\x00\x1074<1\xf4\xb8\xbe\x1074\xbc\x00\x00\x00\x00\xe0\x92\xaa>y\xba\xb2?\xe0\x92\xaa\xbe\x00\x00\x00\x00\x1074\xbc\xae@\xd8\xbe\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00\xc0G\x85>\x00\x00\x00\x80\x00\x00\x80\xbf\x00\x00\x00\x80@]\xe9\xbe^\xd6\xc4\xbf\x00\x00@@\xf8\x02!<\x00\x00\x00\x80\xad\x97\xaa>#\x90\xc1\xbe\xad\x97\xaa\xbe\x00\x00\x00\x00\xf8\x02!<B\x17\xba\xbe\xf8\x02!<\x00\x00\x00\x80\xad\x97\xaa\xbe\x9d\xb5\xb6?\xad\x97\xaa\xbe\x00\x00\x00\x00\xf8\x02!\xbcc\xd3\x9e\xbe\x00\x00\x00\x00\x00\x00\x80?\x00\x00\x00\x00`6\x86>\x00\x00\x00\x80\x00\x00\x80\xbf\x00\x00\x00\x80\xc0\xa5\xe9\xbe\xa5I\xc5\xbf\x00\x00@@\x00\x00\x00\x03\x00\x00HB\x01\x00\x00\x03\x00\x00HB\x02\x00\x00\x03\x00\x00HB\x03\x00\x00\x06\x18\x00\x00\x00\x04\x00\x00\x06\x18\x00\x00\x00\x05\x00\x00\x06\x18\x00\x00\x00\x06\x00\x00\x06\x18\x00\x00\x00\x07\x00\x00\t\x00\x00\x00\x00\x08\x00\x00\x06\x18\x00\x00\x00\t\x00\x00\x06\x18\x00\x00\x00\n\x00\x00\x04(\x00\x00\x00\x0b\x00\x00\t\x00\x00\x00\x00\x0c\x00\x00\t\x00\x00\x00\x00\r\x00\x00\t\x00\x00\x00\x00\x0e\x00\x00\t\x00\x00\x00\x00\x0f\x00\x00\x03\x00\x00\x00\x00\x10\x00\x00\x01\x00\x00\x00\x00\x11\x00\x00\x06\x18\x00\x00\x00\x12\x00\x00\x06\x18\x00\x00\x00\x13\x00\x00\x06\x18\x00\x00\x00\x14\x00\x00\x06\x18\x00\x00\x00\x15\x00\x00\t\x00\x00\x00\x00\x16\x00\x00\x06\x18\x00\x00\x00\x17\x00\x00\x06\x18\x00\x00\x00\x18\x00\x00\x04(\x00\x00\x00\x19\x00\x00\t\x00\x00\x00\x00\x1a\x00\x00\t\x00\x00\x00\x00\x1b\x00\x00\t\x00\x00\x00\x00\x1c\x00\x00\t\x00\x00\x00\x00\x1d\x00\x00\x03\x00\x00\x00\x00\x1e\x00\x00\x01\x00\x00\x00\x00\x1f\x00\x00\x060\x00\x00\x00 \x00\x00\x06@\x00\x00\x00!\x00\x00\x06P\x00\x00\x00"\x00\x00\x06`\x00\x00\x00#\x00\x00\t\x01\x00\x00\x00$\x00\x00\x06p\x00\x00\x00%\x00\x00\x06\x80\x00\x00\x00&\x00\x00\x04\x90\x00\x00\x00\'\x00\x00\t\x00\x00\x00\x00(\x00\x00\t\x00\x00\x00\x00)\x00\x00\t\x00\x00\x00\x00*\x00\x00\t\x00\x00\x00\x00+\x00\x00\x03\x8e\xc8\xac>,\x00\x00\x01\x01\x00\x00\x00-\x00\x00\x06\x98\x00\x00\x00.\x00\x00\x06\xa8\x00\x00\x00/\x00\x00\x06\xb8\x00\x00\x000\x00\x00\x06\xc8\x00\x00\x001\x00\x00\t\x01\x00\x00\x002\x00\x00\x06\xd8\x00\x00\x003\x00\x00\x06\xe8\x00\x00\x004\x00\x00\x04\xf8\x00\x00\x005\x00\x00\t\x01\x00\x00\x006\x00\x00\t\x00\x00\x00\x007\x00\x00\t\x00\x00\x00\x008\x00\x00\t\x00\x00\x00\x009\x00\x00\x03\xa0\xab\x9d>:\x00\x00\x01\x01\x00\x00\x00\x00;\x00\x04\x00\x00\x00k\xb7E?\x00\x00\x80?\x00\x00\x00\x00\x00\x00@\x1f\x80>\x80\x1c\xe00\x01\x04\x18name\x00Weapon\x00preset\x00slot\x00\x0c\x17\xd2\x01main_air_to_air\x00aim_9m_default_slot13\x00aim_120_slot12\x00brimstone_dm_slot10\x00aim_120_slot9\x00aim_120_default_slot8\x00litening\x00aim_120_default_slot6\x00aim_120_slot5\x00brimstone_dm_slot4\x00aim_9m_slot2_x2\x00aim_9m_default_slot1\x00\x00\x00\x00\x01\x00\x00\x00\x00\x02\x00\x00\x01\x10\x00\x00\x00\x03\x00\x00\x02\r\x00\x00\x00\x02\x00\x00\x01&\x00\x00\x00\x03\x00\x00\x02\x0c\x00\x00\x00\x02\x00\x00\x015\x00\x00\x00\x03\x00\x00\x02\n\x00\x00\x00\x02\x00\x00\x01I\x00\x00\x00\x03\x00\x00\x02\t\x00\x00\x00\x02\x00\x00\x01W\x00\x00\x00\x03\x00\x00\x02\x08\x00\x00\x00\x02\x00\x00\x01m\x00\x00\x00\x03\x00\x00\x02\x07\x00\x00\x00\x02\x00\x00\x01v\x00\x00\x00\x03\x00\x00\x02\x06\x00\x00\x00\x02\x00\x00\x01\x8c\x00\x00\x00\x03\x00\x00\x02\x05\x00\x00\x00\x02\x00\x00\x01\x9a\x00\x00\x00\x03\x00\x00\x02\x04\x00\x00\x00\x02\x00\x00\x01\xad\x00\x00\x00\x03\x00\x00\x02\x02\x00\x00\x00\x02\x00\x00\x01\xbd\x00\x00\x00\x03\x00\x00\x02\x01\x00\x00\x00\x00\x01\x0b\x01\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x04\x00\x00\xce\x03\x01\x04\x18name\x00Weapon\x00preset\x00slot\x00\x0c\x17\xd2\x01main_air_to_air\x00aim_9m_default_slot13\x00aim_120_slot12\x00brimstone_dm_slot10\x00aim_120_slot9\x00aim_120_default_slot8\x00litening\x00aim_120_default_slot6\x00aim_120_slot5\x00brimstone_dm_slot4\x00aim_9m_slot2_x2\x00aim_9m_default_slot1\x00\x00\x00\x00\x01\x00\x00\x00\x00\x02\x00\x00\x01\x10\x00\x00\x00\x03\x00\x00\x02\r\x00\x00\x00\x02\x00\x00\x01&\x00\x00\x00\x03\x00\x00\x02\x0c\x00\x00\x00\x02\x00\x00\x015\x00\x00\x00\x03\x00\x00\x02\n\x00\x00\x00\x02\x00\x00\x01I\x00\x00\x00\x03\x00\x00\x02\t\x00\x00\x00\x02\x00\x00\x01W\x00\x00\x00\x03\x00\x00\x02\x08\x00\x00\x00\x02\x00\x00\x01m\x00\x00\x00\x03\x00\x00\x02\x07\x00\x00\x00\x02\x00\x00\x01v\x00\x00\x00\x03\x00\x00\x02\x06\x00\x00\x00\x02\x00\x00\x01\x8c\x00\x00\x00\x03\x00\x00\x02\x05\x00\x00\x00\x02\x00\x00\x01\x9a\x00\x00\x00\x03\x00\x00\x02\x04\x00\x00\x00\x02\x00\x00\x01\xad\x00\x00\x00\x03\x00\x00\x02\x02\x00\x00\x00\x02\x00\x00\x01\xbd\x00\x00\x00\x03\x00\x00\x02\x01\x00\x00\x00\x00\x01\x0b\x01\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x02\x02\x00\x8e\x0b\xabB\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x100\x81C\x07\x10$P\xb1\x83I\x94*X\xb9\x83&\xcf\x1f@\x85\x9bF\xad\x9b\xb8r\xe9\xdb\xc7\xaf\x9f\xc0\x83\n\x1d\x00\x92$\x84\x00\x18\x88\x01\x0e\x14,$\x89)\xc8`\x14\xa1\xa0t\x15\x88\x86)!\x91\x92\x88\x84\x1d \\@\x0e\xe0'
    data = bytes([
        0x53, 0x00, 0x05, 0x30, 0x00, 0x00, 0x0A, 0x74, 0x31, 0x5F, 0x68, 0x65, 0x6C, 0x69, 0x70, 0x61,
        0x64, 0x0E, 0x64, 0x79, 0x6E, 0x41, 0x46, 0x5F, 0x61, 0x72, 0x63, 0x74, 0x69, 0x63, 0x5F, 0x64,
        0x3E, 0x5D, 0x31, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x35, 0x9A, 0x38, 0xBF, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x80, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x35, 0x9A, 0x38, 0x3F, 0x00, 0x00, 0x00, 0x00,
        0x3E, 0x5D, 0x31, 0x3F, 0x29, 0x8C, 0xBC, 0x45, 0x6C, 0xCA, 0x7F, 0xC0, 0x69, 0xEF, 0x54, 0xC2,
        0x80, 0x29, 0xCA, 0x61, 0x60, 0x3C, 0x08, 0x00, 0x32,
    ])
    data = bytes([
        0xAB, 0x01, 0x12, 0x50, 0x01, 0x00, 0x8E, 0xCB, 0xBF, 0x45, 0x00, 0xE5, 0xA3, 0x40, 0x35,
        0x66, 0x21, 0xC3, 0xC4, 0x4C, 0xB9, 0x45, 0x00, 0xF2, 0xA3, 0x40, 0x03, 0xBA, 0x5B, 0x42, 0x0A,
        0x74, 0x31, 0x5F, 0x68, 0x65, 0x6C, 0x69, 0x70, 0x61, 0x64, 0x10, 0x96, 0x42, 0xB9, 0x45, 0x00,
        0x7B, 0xA3, 0x40, 0xE8, 0x1F, 0x0B, 0xC1, 0xD9, 0x44, 0xB9, 0x45, 0x00, 0xD4, 0xA3, 0x40, 0x90,
        0x35, 0xAE, 0x40, 0x07, 0x63, 0xBA, 0x45, 0x00, 0xD7, 0xA3, 0x40, 0xBC, 0x91, 0xCF, 0x41, 0x24,
        0xD4, 0xBA, 0x45, 0x00, 0xD2, 0xA3, 0x40, 0xB0, 0x4E, 0xCD, 0x41, 0x41, 0x45, 0xBB, 0x45, 0x00,
        0xBE, 0xA3, 0x40, 0xA2, 0x0B, 0xCB, 0x41, 0x9A, 0x98, 0xBC, 0x45, 0x00, 0xE9, 0xA2, 0x40, 0x7C,
        0x42, 0xC4, 0x41, 0xB7, 0x09, 0xBD, 0x45, 0x00, 0xA1, 0xA2, 0x40, 0x6E, 0xFF, 0xC1, 0x41, 0xFE,
        0xAF, 0xBD, 0x45, 0x00, 0x4E, 0xA1, 0x40, 0xE8, 0x76, 0x27, 0x40, 0xBB, 0xAD, 0xBD, 0x45, 0x00,
        0x1B, 0xA2, 0x40, 0xEE, 0x5C, 0x38, 0xC1, 0x2B, 0x4B, 0xBF, 0x45, 0x00, 0x65, 0xA4, 0x40, 0x4E,
        0x7D, 0x9F, 0xC2, 0x48, 0xBC, 0xBF, 0x45, 0x00, 0xBE, 0xA3, 0x40, 0x11, 0x0E, 0xA0, 0xC2, 0x65,
        0x2D, 0xC0, 0x45, 0x00, 0xBA, 0xA3, 0x40, 0xD4, 0x9E, 0xA0, 0xC2, 0x1D, 0x97, 0xBD, 0x45, 0x00,
        0xE0, 0xA3, 0x40, 0x78, 0xEA, 0x18, 0xC3, 0x49, 0x0A, 0xBD, 0x45, 0x00, 0x82, 0xA4, 0x40, 0x13,
        0x07, 0x15, 0xC3, 0x2A, 0x5B, 0xBD, 0x45, 0x00, 0xDE, 0xA3, 0x40, 0xC6, 0xFB, 0x2D, 0xC3, 0xCD,
        0x77, 0xBC, 0x45, 0x00, 0xD2, 0xA3, 0x40, 0xD8, 0x7C, 0x34, 0xC3, 0x02, 0x00, 0x00, 0x96, 0x43,
        0x10, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
        0xFF, 0x00, 0x04, 0x00, 0x00, 0x00, 0x04, 0x8E, 0xCB, 0xBF, 0x45, 0x6C, 0xCA, 0x7F, 0xC0, 0x35,
        0x66, 0x21, 0xC3, 0xE7, 0xC3, 0xB8, 0x45, 0x6C, 0xCA, 0x7F, 0xC0, 0x37, 0x7F, 0xBA, 0xC2, 0x9D,
        0x60, 0xBC, 0x45, 0x6C, 0xCA, 0x7F, 0xC0, 0x80, 0x9A, 0x14, 0xC3, 0x61, 0xA7, 0xBE, 0x45, 0x6C,
        0xCA, 0x7F, 0xC0, 0x08, 0x91, 0xE2, 0xC2, 0x04, 0xC4, 0x4C, 0xB9, 0x45, 0x6C, 0xCA, 0x7F, 0xC0,
        0x03, 0xBA, 0x5B, 0x42, 0x34, 0x24, 0xB7, 0x45, 0x6C, 0xCA, 0x7F, 0xC0, 0xB8, 0xA9, 0x1C, 0xC2,
        0x32, 0x67, 0xBB, 0x45, 0x6C, 0xCA, 0x7F, 0xC0, 0xCA, 0x4E, 0xE8, 0xC2, 0xB3, 0x83, 0xBB, 0x45,
        0x6C, 0xCA, 0x7F, 0xC0, 0xC0, 0x92, 0x0B, 0xC1, 0x04, 0x00, 0x00, 0x96, 0x43, 0x00, 0x00, 0xC8,
        0x42, 0x00, 0x00, 0xC8, 0x42, 0x00, 0x00, 0x48, 0x42, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00,
        0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x08, 0x98, 0xD7, 0x3E, 0x12, 0x9D, 0x2B, 0x6B, 0xE3, 0x3A, 0xDF, 0x00, 0x4B, 0x60, 0xB0, 0x22,
        0x03, 0x14, 0x11, 0x00, 0x4A, 0x08, 0x80, 0x31, 0x10, 0x06, 0x22, 0x00, 0x44, 0x40, 0x0C, 0x48,
    ])
    x = IdFieldSerializer255()
    bs = BitStream(data, "outBS.txt", False, True)
    count, end_index = x.readFieldsSizeAndCount(bs)
    x.readFieldsIndex(bs)
    for i in range(count):
        bs.ReadBits(x.sizes[i], "")

    print(x.sizes)
    print(x.indices)
    bs.Flush()