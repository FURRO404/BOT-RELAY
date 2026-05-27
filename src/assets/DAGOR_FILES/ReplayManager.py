from DAGOR_FILES.net.parse_construction import Constructor
from DAGOR_FILES.base.ReplayParser import Data
from DAGOR_FILES.mpi.ParsePlayerMpi import PlayerContainer
from DAGOR_FILES.WtFileUtils.BitStream import BitStream
from DAGOR_FILES.base.idFieldSerializer import *
import zstandard as zstd


class BasicUnitInfo:
    def __init__(self):
        self.air_kills = 0
        self.ground_kills = 0
        self.assists = 0
        self.deaths = 0
        self.captures = 0
        self.score = 0
        self.real_name = None
        self.fake_name = None


class Unit:
    def __init__(self, pid):
        self.player = PlayerContainer()
        self.vehicle_list = []
        self.vehicle = ""
        self.pid: int = pid
        self.info = BasicUnitInfo()
        self.data_dict = {}

    def compile(self):
        if len(self.vehicle_list) > 0:
            self.vehicle = self.vehicle_list[-1]
        else:
            self.vehicle = "dummy_plane"
        self.data_dict = self.player.varList.head.linked_to_dict()
        real_nick = self.player.getVar("realNick").data["str"]
        display_name = self.player.getVar("uid").data["Player_Name"]
        self.info.real_name = display_name
        if real_nick != "" and real_nick != display_name:
            self.info.real_name = real_nick
            self.info.fake_name = display_name




uint8_t = int
uint16_t = int
uint32_t = int
uint64_t = int

ObjectID = uint16_t
ObjectExtUID = uint32_t
MessageID = uint16_t
SystemID = uint8_t

INVALID_OBJECT_ID = 0xFFFF
INVALID_MESSAGE_ID = 0xFFFF
INVALID_SYSTEM_ID = 0xFF
INVALID_OBJECT_EXT_UID = 2 ** 32 - 1  # ~0u

EXT_BIT = 1 << 10


def read_object_ext_uid(bs) -> [ObjectID, ObjectExtUID]:
    ext = INVALID_OBJECT_EXT_UID
    oid = bs.ReadU16("ObjectId")
    if oid is None:
        return INVALID_OBJECT_ID, INVALID_OBJECT_EXT_UID
    # oid = int.from_bytes(bs.ReadBits(ObjectID_s), byteorder='little')
    # if ObjectID == :
    if (oid & EXT_BIT) and oid != INVALID_OBJECT_ID:
        oid ^= EXT_BIT
        ext = bs.ReadUleb("ObjectExtUID")
    return oid, ext


def decompress_zstd(bs: BitStream):
    # print("DECOMPRESSING")
    comp_size = bs.ReadUleb("Compressed_size")
    decomp_size = bs.ReadUleb("Decompressed_size")
    return BitStream(zstd.decompress(bs.ReadBytes(comp_size, "ZSTD_Compressed_Data"), decomp_size), "", False, False)


class ReplayManager:
    ReflectionNoDecompress = 0xf0aa
    Reflection1 = 0xf02d
    Reflection2 = 0xd136

    def __init__(self):
        self.Units = [Unit(_) for _ in range(0, 16)]  # 16 players
        self.constructor = Constructor()

    def deserializeReflectables(self, bs: BitStream):
        numReflectables: uint16_t = bs.ReadU16("numReflectables")
        if numReflectables is None:
            return -1
        for i in range(numReflectables):
            data_written = bs.ReadU16("dataWritten")
            if data_written is None:
                return -2
            assert BITS_TO_BYTES(bs.RemainingBits()) >= data_written
            if BITS_TO_BYTES(bs.RemainingBits()) < data_written:
                return -3
            start_pos: BitSize_t = bs.GetReadOffset()
            oid, extUid = read_object_ext_uid(bs)
            startPosAfterId: BitSize_t = bs.GetReadOffset()
            # here is where dispatch normally happens
            shifted = oid >> 0xb
            if shifted > 0x19:
                return -4
            lower_bits_data = oid & 0x7FF
            if shifted == 0xe:  # player refl
                if lower_bits_data < len(self.Units):
                    self.Units[lower_bits_data].player.deserialize(bs, 0)
            bs.SetReadOffset(start_pos)
            bs.IgnoreBytes(data_written)
            # bs.ReadBytes(data_written, "")
        return numReflectables

    def handleMpi(self, pkt: Data):
        bs = pkt.get_bitstream()
        oid, extUid = read_object_ext_uid(bs)
        mid = bs.ReadU16("MessageID")

        shifted = oid >> 0xb
        if shifted > 0x19:
            return None
        lower_bits_data = oid & 0x7FF
        if shifted == 0xb and lower_bits_data == 0x2:  # main mpi handler, handles reflection
            match mid:
                case self.ReflectionNoDecompress:
                    return self.deserializeReflectables(bs)
                case self.Reflection1:
                    is_compressed = bs.ReadU8("ReflectableIsCompressed") == 1
                    if is_compressed:
                        bs = decompress_zstd(bs)
                    return self.deserializeReflectables(bs)
                case self.Reflection2:
                    is_compressed = bs.ReadU8("ReflectableIsCompressed") == 1
                    if is_compressed:
                        bs = decompress_zstd(bs)
                    return self.deserializeReflectables(bs)

    def OnPacket(self, pkt: Data):
        match pkt.p_type:
            case 0x4:
                self.handleMpi(pkt)
            case 0x6:
                t, payload = self.constructor.OnPacket(pkt)
                if t != "C":
                    return
                for unit in payload:
                    unit: dict
                    pid, vehicle = unit.get(13)[0], unit.get(6)[1:]  # type:ignore
                    if pid == 0xFF:
                        continue
                    if vehicle != b"dummy_plane" and b"recon_micro" not in vehicle:
                        self.Units[pid].vehicle_list.append(vehicle.decode("utf-8"))
                        self.Units[pid].pid = pid

    def FullyParsed(self):
        for unit in self.Units:
            if len(unit.vehicle_list) == 0:
                return False
        return True

    def finalise(self):
        for unit in self.Units:
            unit.compile()

    def getPlayerTag(self, pid: int):
        if pid >= len(self.Units):
            return ""
        return self.Units[pid].player.getVar("clanTag").data["str"]

    def getPlayerTeam(self, pid: int):
        if pid >= len(self.Units):
            return -1
        return self.Units[pid].player.getVar("team").data["team"]

    def getTeamTag(self, pid: int):
        player_tag = self.getPlayerTag(pid)
        if player_tag == "":
            team = self.getPlayerTeam(pid)
            for unit in self.Units:
                if self.getPlayerTeam(unit.pid) == team:
                    player_tag = self.getPlayerTag(unit.pid)
                    if player_tag != "":
                        return player_tag
        else:
            return player_tag

    def getAllTags(self):
        payload = set()
        for unit in self.Units:
            unit_tag = self.getPlayerTag(unit.pid)
            if unit_tag != "":
                payload.add(unit_tag)
        return list(payload)

    def getTeams(self) -> tuple[list[Unit], list[Unit]]:
        team1 = []
        team2 = []
        for unit in self.Units:
            team = self.getPlayerTeam(unit.pid)
            if team == 1:
                team1.append(unit)
            elif team == 2:
                team2.append(unit)
        return team1, team2
