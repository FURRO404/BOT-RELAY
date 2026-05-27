from DAGOR_FILES.base.ReplayParser import Replay_Extended, get_server_eid, Data
from DAGOR_FILES.base.idFieldSerializer import IdFieldSerializer255
from DAGOR_FILES.WtFileUtils.BitStream import BitStream

import lz4.block._block as lz4
import os



_GLOBAL_DO_WRITE_FILE = True


class bitVector:
    def __init__(self, size):
        self.data = [False for x in range(size)]

    def test(self, n, defaultValue): # // Returns true if the bit index is < size() and set. Returns defaultValue if the bit is >= size().
        if n+1 <= len(self.data):
            return self.data[n]
        return defaultValue

    def set(self, n, value): # // Resizes the container to accomodate n if necessary.
        if n+1 > len(self.data):
            self.data.extend([False for x in range((n+1)-len(self.data))])
        self.data[n] = value


class ConstructedObject:
    def __init__(self, name, bs):
        pass

    def deconstruct(self, obj):
        pass

class Packet_Types:
    ID_CONNECTION_REQUEST_ACCEPTED = 0x11
    ID_DISCONNECT = 0x13
    ID_ENTITY_MSG = 0x20
    ID_ENTITY_MSG_COMPRESSED = 0x21
    ID_ENTITY_REPLICATION = 0x22
    ID_ENTITY_REPLICATION_COMPRESSED = 0x23
    ID_ENTITY_CREATION = 0x24
    ID_ENTITY_CREATION_COMPRESSED = 0x25
    ID_ENTITY_DESTRUCTION = 0x26
    IS_COMPRESSED = [ID_ENTITY_MSG_COMPRESSED, ID_ENTITY_REPLICATION_COMPRESSED, ID_ENTITY_CREATION_COMPRESSED]

class Constructor:
    count = 0
    def __init__(self, all_construction = True, basic_construction = True):
        self.all_construction = all_construction
        self.basic_construction = basic_construction
        self.componentsSynced = bitVector(0)
        self.serverToClientCidx = []
        self.serverTemplates = {}
        self.clientTemplatesComponents = {}
        self.constructed_objects: list[ConstructedObject] = []
        self.replicated_objects: dict = {}
        self.destructed_objects = []
        self.players = {i: [] for i in range(128)}
        self.componentsSynced = bitVector(0)
        self.on_constructed_obj = []

    def register_on_constructed_object(self, func):
        self.on_constructed_obj.append(func)

    @staticmethod
    def read_component_index(bs: BitStream):

        return bs.ReadUleb("component_index") # bs.ReadUleb(max=3, desc="component_index")


    def syncReadComponent(self, serverCidx, bs: BitStream, templateId, error):
        name = bs.ReadU32("comp_name")
        type_ = bs.ReadU32("comp_type")
        # cidx = self.index_name_id(name, type_, self.serverTemplates[templateId])
        cidx = -1
        if serverCidx >= len(self.serverToClientCidx):
            self.serverToClientCidx.extend([None for x in range(1+serverCidx - len(self.serverToClientCidx))])
        self.serverToClientCidx[serverCidx] = cidx
        self.componentsSynced.set(serverCidx, True)

    def syncReadTemplate(self, bs: BitStream, template_id):
        self.serverTemplates[template_id] = bs.ReadPascalStr("ServerTemplName")
        # print("new template: ", self.serverTemplates[template_id])
        componentsInTemplate = bs.ReadU16("components_in_template")
        self.clientTemplatesComponents[template_id] = [None for x in range(componentsInTemplate)]
        for cid in range(componentsInTemplate):
            serverCidx = self.read_component_index(bs)  # uint16
            name = self.serverToClientCidx[serverCidx] if serverCidx < len(self.serverToClientCidx) else None

            # print(f"serverCidx: {hex(serverCidx)}, cliCidx: {cliCidx}")
            if name is not None:
                self.clientTemplatesComponents[template_id][cid] = name
            elif not self.componentsSynced.test(serverCidx, False):
                self.syncReadComponent(serverCidx, bs, template_id,
                                  False)  # going to assume False cause dont feel like doing that
                self.clientTemplatesComponents[template_id][cid] = self.serverToClientCidx[serverCidx]

    def deserializeTemplate(self, bs: BitStream):  # not including template_id
        template_id = bs.ReadUleb("template_id")
        if template_id not in self.serverTemplates: # if template_id >= len(self.serverTemplates):
            # urrent_index = bs.GetReadOffset()
            # bs.SetReadOffset(current_index)
            self.syncReadTemplate(bs, template_id)
        # print(f"deserializing: {self.serverTemplates[template_id]}")
        return self.serverTemplates[template_id], template_id

    def deserialize_construction(self, bs: BitStream, eid) -> dict:
        templName, templete_id = self.deserializeTemplate(bs)
        if templName in [b'aircraft+player_unit', b'tank+player_unit']:
            if len(self.clientTemplatesComponents[templete_id]) > 255:
                bs.ReadUleb()
            else:
                bs.ReadU8()
            bs.ReadU8()
            sz = bs.ReadUleb()
            # bs = BitStream(bs.ReadBits(sz))
            payload = {}
            idFieldSerializer = IdFieldSerializer255()
            numVars, end_pos = idFieldSerializer.readFieldsSizeAndCount(bs)
            idFieldSerializer.readFieldsIndex(bs)
            # print(numVars, end_pos)
            for i in range(numVars):
                sz, field_id = idFieldSerializer.getFieldSize(i), idFieldSerializer.getFieldId(i)
                payload.update({field_id: bs.ReadBits(sz)})
            return payload


    def readConstructionPacket(self, bs: BitStream) -> list[ConstructedObject]:
        written = bs.ReadU8("entry_count")
        # written = bs.ReadBits(8, desc="entry_count")
        packets = []
        for i in range(written + 1):
            # print(bs.GetReadOffset())
            server_eid = get_server_eid(bs)
            blockSizeBytes = bs.ReadUleb("block_size") << 3

            startpos = bs.GetReadOffset()
            # print(blockSizeBytes)
            out = self.deserialize_construction(bs, server_eid)
            if out:
                packets.append(out)
            bs.SetReadOffset(startpos + blockSizeBytes)
        return packets


    def message_apply(self, bs: BitStream):
        serverEid = get_server_eid(bs)
        # nClsIdBits

    def bitstream_decompress(self, bs: BitStream) -> BitStream:
        assert bs.GetReadOffset() & 7 == 0

        # compressedSize =
        return BitStream(lz4.decompress(bs.ReadRemaining("compressedData"), 0xFFFFF))

    def OnPacket(self, packet: Data):
        if packet.p_type not in b"\x06\x16":
            raise Exception("Invalid packet type")
        bs = packet.get_bitstream()

        ptype = bs.ReadU8("Net_Packet_Type")
        decompressed_ptype = ptype
        match decompressed_ptype: # this just lets the match case down below only match to decompressed_type
            case Packet_Types.ID_ENTITY_REPLICATION_COMPRESSED:
                decompressed_ptype = Packet_Types.ID_ENTITY_REPLICATION
            case Packet_Types.ID_ENTITY_CREATION_COMPRESSED:
                decompressed_ptype = Packet_Types.ID_ENTITY_CREATION
            case Packet_Types.ID_ENTITY_MSG_COMPRESSED:
                decompressed_ptype = Packet_Types.ID_ENTITY_MSG


        '''
        blame gaijin for this horrific lambda
        TLDR when its called, you pass it the compressed type for this packet
        if the compress type doesnt match the current packet's type, then the current packet is not compressed
        otherwise decompress
        '''
        readCompressedIfPacketType = lambda ctype : \
            bs if ptype != ctype else \
            self.bitstream_decompress(bs)
        # print(hex(ptype))


        match decompressed_ptype:
            case Packet_Types.ID_ENTITY_CREATION:
                bsToRead = readCompressedIfPacketType(Packet_Types.ID_ENTITY_CREATION_COMPRESSED)
                return ["C", self.readConstructionPacket(bsToRead)]
        return ["N", None]

    def parse_construct_file(self, packet: Data):
        if packet.p_type not in b"\x06\x16":
            return
        bs = BitStream(packet.data)
        t = bs.ReadU8()
        if t in [Packet_Types.ID_ENTITY_CREATION, Packet_Types.ID_ENTITY_CREATION_COMPRESSED]:
            if t == Packet_Types.ID_ENTITY_CREATION_COMPRESSED:
                bs = BitStream(lz4.decompress(bs.ReadRemaining(), 0xFFFF))
            v = self.readConstructionPacket(bs)
            path = f"out/{Constructor.count}"

            with open(f"{path}.bin", "wb") as f:
                f.write(bs.GetData())
            # print("count:", Constructor.count)
            for x in v:
                pass
                # print(x.objects.get("unit__className", None))
                # print(x.objects.keys())
            Constructor.count += 1
