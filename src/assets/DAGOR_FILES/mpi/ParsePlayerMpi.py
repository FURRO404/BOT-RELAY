from DAGOR_FILES.WtFileUtils.BitStream import BitStream
from DAGOR_FILES.base.ReplayParser import get_server_eid
from DAGOR_FILES.WtFileUtils.blk.BlkParser import BlkParser
from DAGOR_FILES.base.idFieldSerializer import *

uint8_t = int
uint16_t = int
uint32_t = int
uint64_t = int


DANET_REFLECTION_MAX_VARS_PER_OBJECT = 255
DANET_REPLICATION_MAX_CLASSES = 256
DANET_REFLECTION_OP_ENCODE = 0  #  encode data
DANET_REFLECTION_OP_DECODE = 1  #  decode data
reflection_var_encoder = type(lambda _: _)

class LinkedIter: # used for iterating over ReflectionVarMeta easily
    def __init__(self, head):
        self.head = head

    def __iter__(self):
        return self

    def __next__(self):
        ret = self.head
        if ret:
            self.head = self.head.next
            return ret
        raise StopIteration

class ReflectionVarMeta:
    def __init__(self, id_, flags, num_bits, name, coder):
        self.persistentId: uint8_t = id_
        self.flags: uint16_t = 0
        self.numBits: uint16_t = num_bits
        self.name: str = name
        self.coder: reflection_var_encoder = coder
        self.next: ReflectionVarMeta | None = None
        self.data = {} # I made this field

    def getVarName(self):
        return self.name

    def __iter__(self):
        return LinkedIter(self)

    def to_dict(self):
        return {self.getVarName() : self.data}

    def linked_to_dict(self):
        payload = {}
        for var in self:
            payload.update(var.to_dict())
        return payload



def PlayerCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        # offset = bs.GetReadOffset()
        # print("Player:::", bs.ReadBytes(100))
        # bs.SetReadOffset(offset)
        meta.data["uid"] = bs.ReadU32()
        bs.IgnoreBytes(4)  # dunno whats here
        meta.data["Player_Name"] = bs.ReadBytes(65).rstrip(b"\x00").decode("utf-8", errors="ignore")
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def PStringCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["str"] = bs.ReadPascalStr(f"{meta.getVarName()}_CoderStr").decode("utf-8", errors="ignore")
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def TranslatedCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        PStringCoder(op, meta, bs)
        # do stuff with vromfs maybe here
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def t20orLessCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        size = meta.numBits if meta.numBits < 0x20 else 0x20
        meta.data["t20"] = bs.ReadBitsInt(size)
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True

def t20Coder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        size = 0x20
        meta.data["t20"] = bs.ReadBitsInt(size)
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def DataBlockCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        size = bs.ReadUleb()
        # print(f"DBlk size {size}")
        if size:
            meta.data["DataBlock"] = BlkParser(
                bs).to_dict()  #TODO: When datablock class is changed to be proper, make this store the datablock
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def TeamU8Coder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["team"] = bs.ReadU8(f"TeamCoder")
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def countryCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["country"] = bs.ReadU8(f"CountryCoder")
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def U16Coder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["U16"] = bs.ReadU16(f"{meta.getVarName()}_U16Coder")
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def CustomStateCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        size = bs.ReadUleb()
        # print(f"DBlk size {size}")
        if size:
            meta.data["CustomState"] = BlkParser(bs).to_dict()
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def dummyForSupportPlanesCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        for i in range(4):
            meta.data[f"dummyForSupportPlanesEid{i}"] = \
                (hex(get_server_eid(bs)), hex(get_server_eid(bs)), hex(get_server_eid(bs)), hex(get_server_eid(bs)),
                 hex(get_server_eid(bs)))
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def otherU8Coder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["otherU8"] = bs.ReadU8(f"OtherU8Coder")
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def othert20orLessCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        size = meta.numBits if meta.numBits < 0x20 else 0x20
        if size == 0x20:
            meta.data["othert20"] = bs.ReadFloat()
        else:
            meta.data["othert20"] = bs.ReadBits(size)
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def NothingCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    # print("NOTHING HAPPENS")
    return False

def BoolCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["bool"] = bs.ReadBool()
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def dummyForCountUsedSlotsCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        count = bs.ReadU8("Count")
        meta.data["dummyForCountUsedSlots"] = [bs.ReadU8("DummyForCountData") for x in range(count)]
    elif op == DANET_REFLECTION_OP_ENCODE:
        raise NotImplementedError()
    return True


def dummyForSpawnCostsCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        count = bs.ReadU8("Count")
        meta.data["dummyForSpawnCosts"] = [bs.ReadU32("dummyForSpawnCosts") for x in range(count)]
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True


def dummyForSpawnDelayTimesCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        count = bs.ReadU8("Count")
        meta.data["dummyForSpawnDelayTimes"] = [bs.ReadU16("dummyForSpawnDelayTimes") for x in range(count)]
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True


def dummyForKillStreaksProgressCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        # return False  # I dunno
        count = bs.ReadU8("Count")
        meta.data["dummyForKillStreaksProgress"] = [bs.ReadU8("dummyForKillStreaks") for x in range(count)]
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True


def dummyForRoundScoreCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["0x20"] = bs.ReadU32("0x20")
        count = bs.ReadU8("Count")
        # print(count, meta.data["0x20"])
        meta.data["dummyForRoundScore"] = [bs.ReadU32("dummyForRoundScore") for x in range(count)]
        # print(meta.data)
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True


def EidCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["Eid"] = hex(get_server_eid(bs))
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True
def stateCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["state"] = bs.ReadU16("state")
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True



def dummyForPlayerStatCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["dummyForPlayerStat1"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat2"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat3"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat4"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat5"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat6"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat7"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat8"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat9"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat10"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat11"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat12"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat13"] = bs.ReadU32("dummyForPlayerStat")
        meta.data["dummyForPlayerStat14"] = bs.ReadU32("dummyForPlayerStat")
        meta.data["dummyForPlayerStat15"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat16"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat17"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat18"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat19"] = bs.ReadU32("dummyForPlayerStat")
        meta.data["dummyForPlayerStat20"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat21"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat22"] = bs.ReadU16("dummyForPlayerStat")
        meta.data["dummyForPlayerStat23"] = bs.ReadU16("dummyForPlayerStat")
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True


def dummyForFootballStatCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["FootballStat"] = bs.ReadU16("FootballStat")
        meta.data["FootballStat1"] = bs.ReadU16("FootballStat")
        meta.data["FootballStat2"] = bs.ReadU16("FootballStat")
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True

def forceLockTargetCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["Target"] = bs.ReadU16("Target")
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True


def xuidCoder(op: int, meta: ReflectionVarMeta, bs: BitStream):
    if op == DANET_REFLECTION_OP_DECODE:
        meta.data["xuid"] = bs.ReadBitsInt(0x40)
    elif op == DANET_REFLECTION_OP_ENCODE:
        pass
    return True

class VarList:
    def __init__(self, head, tail):
        self.head: ReflectionVarMeta = head
        self.tail: ReflectionVarMeta = tail


class PlayerContainer:
    def __init__(self):
        self.team = None
        self.varList: VarList = VarList(None, None)

        refl2 = ReflectionVarMeta(2,0, 584, "uid", PlayerCoder)
        refl3 = ReflectionVarMeta(3,0, 64, "invitedNickName", PStringCoder)
        refl4 = ReflectionVarMeta(4,0, 64, "nickLocKey", TranslatedCoder)
        refl5 = ReflectionVarMeta(5,0, 64, "clanTag", PStringCoder)
        refl6 = ReflectionVarMeta(6,0, 64, "title", PStringCoder)
        refl7 = ReflectionVarMeta(7,0, 32, "publicFlags", t20orLessCoder)
        refl8 = ReflectionVarMeta(8,0, 64, "decals", DataBlockCoder)
        refl9 = ReflectionVarMeta(9,0, 8, "team", TeamU8Coder)
        refl10 = ReflectionVarMeta(10,0, 8, "countryId", countryCoder)
        refl11 = ReflectionVarMeta(11,0, 16, "memberId", U16Coder)
        refl12 = ReflectionVarMeta(12,0, 64, "customState", CustomStateCoder)
        refl13 = ReflectionVarMeta(13,0, 16, "score", U16Coder)
        refl14 = ReflectionVarMeta(14,0, 32, "dummyForSupportPlanes", dummyForSupportPlanesCoder)
        refl15 = ReflectionVarMeta(15,0, 32, "dummyForCrewUnitsList", NothingCoder)
        refl16 = ReflectionVarMeta(16,0, 32, "disabledByMatchingSlots", t20orLessCoder)
        refl17 = ReflectionVarMeta(17,0, 32, "brokenSlots", t20orLessCoder)
        refl18 = ReflectionVarMeta(18,0, 32, "wasReadySlots", t20orLessCoder)
        refl19 = ReflectionVarMeta(19,0, 32, "spareAircraftInSlots", t20orLessCoder)
        refl20 = ReflectionVarMeta(20,0, 32, "ownedSlots", t20orLessCoder)
        refl21 = ReflectionVarMeta(21,0, 8, "classinessMark", otherU8Coder)
        refl22 = ReflectionVarMeta(22,0, 32, "timeToRespawn", othert20orLessCoder)
        refl23 = ReflectionVarMeta(23,0, 32, "timeToRespawnInCoop", othert20orLessCoder)
        refl24 = ReflectionVarMeta(24,0, 8, "forcedRespawn",BoolCoder)
        refl25 = ReflectionVarMeta(25,0, 32, "timeToKick", othert20orLessCoder)
        refl26 = ReflectionVarMeta(26,0, 8, "guiState", otherU8Coder)
        refl27 = ReflectionVarMeta(27,0, 32, "spectatedModelIndex", t20orLessCoder)
        refl28 = ReflectionVarMeta(28,0, 32, "dummyForCountUsedSlots", dummyForCountUsedSlotsCoder)
        refl29 = ReflectionVarMeta(29,0, 32, "dummyForSpawnCosts", dummyForSpawnCostsCoder)
        refl30 = ReflectionVarMeta(30,0, 32, "dummyForSpawnDelayTimes", dummyForSpawnDelayTimesCoder)
        refl31 = ReflectionVarMeta(31,0, 32, "dummyForKillStreaksProgress", dummyForKillStreaksProgressCoder)
        refl32 = ReflectionVarMeta(32,0, 8, "state", stateCoder)
        refl33 = ReflectionVarMeta(33,0, 32, "squadScore", t20orLessCoder)
        refl34 = ReflectionVarMeta(34,0, 128, "ownedUnitRef", EidCoder)
        refl35 = ReflectionVarMeta(35,0, 128, "controlledUnitRef", EidCoder)
        refl36 = ReflectionVarMeta(36,0, 128, "supportUnitRef", EidCoder)
        refl37 = ReflectionVarMeta(37,0, 128, "wreckedPartShipUnitRef", EidCoder)
        refl38 = ReflectionVarMeta(38,0, 32, "dummyForRoundScore",dummyForRoundScoreCoder )
        refl39 = ReflectionVarMeta(39,0, 32, "dummyForPlayerStat", dummyForPlayerStatCoder)
        refl40 = ReflectionVarMeta(40,0, 32, "dummyForFootballStat", dummyForFootballStatCoder)
        refl41 = ReflectionVarMeta(41,0, 64, "realNick", PStringCoder)
        refl42 = ReflectionVarMeta(42,0, 32, "squadronId", t20orLessCoder)
        refl43 = ReflectionVarMeta(43,0, 64, "forceLockTarget", forceLockTargetCoder)
        refl44 = ReflectionVarMeta(44,0, 8, "cachedIsAutoSquad", BoolCoder)
        refl45 = ReflectionVarMeta(45,0, 64, "xuid", xuidCoder)
        refl46 = ReflectionVarMeta(46,0, 64, "nickFrame", PStringCoder)
        refl47 = ReflectionVarMeta(47,0, 128, "missionSupportUnitRef", EidCoder)
        refl48 = ReflectionVarMeta(48,0, 8, "missionSupportUnitEnabled", BoolCoder)
        refl49 = ReflectionVarMeta(49,0, 16, "rageTokens", U16Coder)
        refl2.next = refl3
        refl3.next = refl4
        refl4.next = refl5
        refl5.next = refl6
        refl6.next = refl7
        refl7.next = refl8
        refl8.next = refl9
        refl9.next = refl10
        refl10.next = refl11
        refl11.next = refl12
        refl12.next = refl13
        refl13.next = refl14
        refl14.next = refl15
        refl15.next = refl16
        refl16.next = refl17
        refl17.next = refl18
        refl18.next = refl19
        refl19.next = refl20
        refl20.next = refl21
        refl21.next = refl22
        refl22.next = refl23
        refl23.next = refl24
        refl24.next = refl25
        refl25.next = refl26
        refl26.next = refl27
        refl27.next = refl28
        refl28.next = refl29
        refl29.next = refl30
        refl30.next = refl31
        refl31.next = refl32
        refl32.next = refl33
        refl33.next = refl34
        refl34.next = refl35
        refl35.next = refl36
        refl36.next = refl37
        refl37.next = refl38
        refl38.next = refl39
        refl39.next = refl40
        refl40.next = refl41
        refl41.next = refl42
        refl42.next = refl43
        refl43.next = refl44
        refl44.next = refl45
        refl45.next = refl46
        refl46.next = refl47
        refl47.next = refl48
        refl48.next = refl49
        self.varList.head = refl2
        self.varList.tail = refl49

    def getDebugName(self):
        return self.__class__.__name__

    def onBeforeVarsDeserialization(self):
        return True

    def onAfterVarsDeserialization(self):
        return True

    def getVarByPersistentId(self, id: int) -> ReflectionVarMeta:
        start = self.varList.head
        while start is not None:
            if start.persistentId == id:
                return start
            start = start.next

    def getVar(self, name):
        start = self.varList.head
        while start is not None:
            if start.getVarName() == name:
                return start
            start = start.next

    def deserialize(self, bs: BitStream, data_size: int):
        end_pos: BitSize_t = 0
        idFieldSerializer = IdFieldSerializer255()
        numVars, end_pos = idFieldSerializer.readFieldsSizeAndCount(bs)
        # print(numVars, end_pos)
        idFieldSerializer.readFieldsIndex(bs)
        varsToRead: list[ReflectionVarMeta] | list[None] = [None] * numVars
        # print("deserialzing vars: ", end="")
        for i in range(numVars):
            v = self.getVarByPersistentId(idFieldSerializer.getFieldId(i))
            # print(v.getVarName())
            varsToRead[i] = v
            # if(v):
            #     print(f"{v.getVarName()}; ", end="")
        # print()

        # print(f"VARS BEING REFLECTED FOR {self.getDebugName()}")
        # print(', '.join([x.getVarName() for x in varsToRead if x]))


        self.onBeforeVarsDeserialization()

        ret = True

        for j in range(numVars):
            ppp = bs.GetReadOffset()
            v: ReflectionVarMeta = varsToRead[j]
            if not v:
                idFieldSerializer.skipReadingField(j, bs)
                continue
            assert v.coder
            # print(f"ATTEMPTING TO DESERIALIZE {v.getVarName()}")
            if not v.coder(DANET_REFLECTION_OP_DECODE, v, bs):
                # debug("can't decode value for var '%s' in obj 0x%p (type = '%s')", v->getVarName(), this, getClassName());
                if False:
                    print(f"Can't decode value for var {v.getVarName()} in obj {self.getDebugName()}, size: {idFieldSerializer.getFieldSize(j)}")
                idFieldSerializer.skipReadingField(j, bs)  # skip
                continue
            # print(bs.GetReadOffset()-ppp, idFieldSerializer.getFieldSize(j))
            if bs.GetReadOffset() - ppp != idFieldSerializer.getFieldSize(j):
                ret = False
                if v.getVarName() in []:
                    pass
                else:
                    pass
                    # print(f"Var {v.getVarName()} deserialized not according to field seralizer ("
                    #            f"{bs.GetReadOffset() - ppp}, {idFieldSerializer.getFieldSize(j)})") # assert
                bs.SetReadOffset(ppp+idFieldSerializer.getFieldSize(j))
                # break

            #  print(f"Deseralized {v.getVarName()} for obj {self.getDebugName()}")
        # dont do correct flags cause I dont know all places where flags are modified
        self.onAfterVarsDeserialization()
        bs.SetReadOffset(end_pos)
        return ret