

import lz4.block._block as lz4
import zstandard as zstd


if __name__ == "__main__":
    from DAGOR_FILES.WtFileUtils.BitStream import BitStream
    from ReplayOpener import Replay
    from idFieldSerializer import BITS_TO_BYTES
else:
    from DAGOR_FILES.WtFileUtils.BitStream import BitStream
    from .ReplayOpener import Replay
    from .idFieldSerializer import BITS_TO_BYTES

ENTITY_INDEX_BITS = 22
ENTITY_INDEX_MASK = (1 << ENTITY_INDEX_BITS) - 1
ENTITY_GENERATION_BITS = 8
ENTITY_GENERATION_MASK = (1 << ENTITY_GENERATION_BITS) - 1


def make_eid(index, gen):
    return index | (gen << ENTITY_INDEX_BITS)


def get_server_eid(bitstream: BitStream, name=""):
    first16Bit = int.from_bytes(bitstream.ReadBits(16, f"{name}_server_eid_first_half"), byteorder='little')
    size = 2
    eidVal = 0
    # print(f"eid is type: {'first' if first16Bit & 1 else ('second' if first16Bit & 2 else 'third')}")
    if first16Bit & 1:  # 2 byte
        eidVal = make_eid(first16Bit >> 2, (first16Bit & 2) >> 1)
    elif first16Bit & 2:  # short eid
        generation = int.from_bytes(bitstream.ReadBits(8, f"{name}_server_eid_short"), byteorder='little')
        size = 3
        eidVal = make_eid(first16Bit >> 2, generation)
    else:  # long eid, 4: byte version
        tailData = int.from_bytes(bitstream.ReadBits(16, f"{name}_server_eid_tail"), byteorder='little')
        compressedData = (tailData << 16) | first16Bit
        eidVal = make_eid((compressedData & 0x00ffffff) >> 2, compressedData >> 24)
        size = 4
    # bitstream.advance(size*8*-1)
    # print(f"bytes: {bitstream.fetch(size*8).hex()}, eid: {hex(eidVal)}")
    return eidVal


def get_val(data: BitStream):
    '''
    a basic packet parser, will extract the size bytes
    this was reverse engineered from the warthunder binary
    :param data: a DataHandler, its current index should be the start of the packet size data
    :return: a list[int, bytes]. the integer is the size value while the bytes is what made up that integer as in the data
    '''
    byte_ = data.ReadU8("PacketSizeStart")
    if byte_ & 0x80:
        return byte_ & 0x7f, bytes([byte_])  #js, jump signed
    else:
        num = 1
        if byte_ & 0x40 == 0:
            num = 2
            if byte_ & 0x20 == 0:
                num = 3
                if byte_ & 0x10 == 0:
                    num = 4
                pass
            pass  # check for this option
        new_dat = data.ReadBytes(num, "PacketSizeExtra")
        if byte_ & 0x80:
            pass  # goto start???
        if byte_ & 0x40 == 0:
            if byte_ & 0x20 == 0:
                if byte_ & 0x10 == 0:
                    return new_dat[0] + (new_dat[1] << 8) + (new_dat[2] << 16) + (new_dat[3] << 24), bytes(
                        [byte_, *new_dat])
                    pass
                else:
                    print("ONE")
                    pass
            else:
                return (new_dat[1] + (byte_ << 0x10) + (new_dat[0] << 0x8)) ^ 0x200000, bytes([byte_, *new_dat])
                pass
        else:
            return ((byte_ << 8) + new_dat[0]) ^ 0x4000, bytes([byte_, *new_dat])


def get_val_no_bs(data):
    '''
    a basic packet parser, will extract the size bytes
    this was reverse engineered from the warthunder binary
    :param data: a DataHandler, its current index should be the start of the packet size data
    :return: a list[int, bytes]. the integer is the size value while the bytes is what made up that integer as in the data
    '''
    byte_ = data[0]
    if byte_ & 0x80:
        return byte_ & 0x7f, bytes([byte_]).hex()  #js, jump signed
    else:
        num = 1
        if byte_ & 0x40 == 0:
            num = 2
            if byte_ & 0x20 == 0:
                num = 3
                if byte_ & 0x10 == 0:
                    num = 4
                pass
            pass  # check for this option
        new_dat = data[1:num + 1]
        if byte_ & 0x40 == 0:
            if byte_ & 0x20 == 0:
                if byte_ & 0x10 == 0:
                    return new_dat[0] + (new_dat[1] << 8) + (new_dat[2] << 16) + (new_dat[3] << 24), bytes(
                        [byte_, *new_dat]).hex()
                    pass
                else:
                    print("ONE")
                    pass
            else:
                return (new_dat[1] + (byte_ << 0x10) + (new_dat[0] << 0x8)) ^ 0x200000, bytes([byte_, *new_dat]).hex()
                pass
        else:
            return ((byte_ << 8) + new_dat[0]) ^ 0x4000, bytes([byte_, *new_dat]).hex()


def build_val(size_t: int):
    # print(size_t)
    x = None
    if size_t > 0xFFFFFFF:  # > 0xFFFFFF
        num = size_t
        return b"00" + size_t.to_bytes(4, "little")
    elif size_t > 0xFFFFF:  # > 0xFFFF
        num = 0x10000000 | size_t
        return num.to_bytes(4, "little")
    elif size_t > 0xFFF:
        num = 0x200000 | size_t
        return num.to_bytes(3, byteorder='big')
    elif size_t > 0x3F:
        num = 0x4000 | size_t
        return num.to_bytes(2, byteorder='big')
    elif size_t < 0x40:
        return (size_t | 0x80).to_bytes(1, byteorder='little')
    else:
        return b""



class Data:
    def __init__(self, p_type, data, time, time_has):
        self.p_type: int = p_type
        self.data: bytearray = bytearray(data)
        self.time: int = time
        self.time_has = time_has
        self.id_ = 0
        self.include = True

    def get_packet_full(self):
        if not self.time_has:
            return build_val(len(self.data) + 2) + self.p_type.to_bytes(byteorder="little") + b"\x00" + self.data
        return build_val(len(self.data) + 2 + 4) + (self.p_type ^ 0x10).to_bytes(
            byteorder="little") + b"\x00" + self.time.to_bytes(4, byteorder="little") + self.data

    def get_bitstream(self):
        return BitStream(bytes(self.data))

    def get_time(self):
        return self.time / 1000

    def remove(self):
        """
        a variable used by the Parser when rebuilding internal, doesnt include this packet
        """
        self.include = False


class Replay_Extended:
    def __init__(self, path):
        self.path = path
        self.replay = Replay(path)
        self.packets: list[Data] = []
        if not self.replay.is_good:
            raise Exception("Replay is not good")

        data = BitStream(self.replay.zlib_data, "out.txt", False, False)
        count_ = 0
        # with open("temp.txt", "w") as f:
        index = 0
        prev_packet = Data(0, b"", 0, False)
        while data.RemainingBits() > 0:
            #  f.write(f"u8 a{count_}[{hex(out[0])}] @ {hex(data.get_ptr())};\n")
            try:
                out = get_val(data)
            except Exception as e:
                break
            # raw_len = out[1]
            start = data.GetReadOffset()
            end_index = BITS_TO_BYTES(start)+out[0]
            p_type = data.ReadU16("ReplayPacketType")
            # p_type = z.fetch(1)[0]
            time = None
            has_time = False
            if p_type & 0x10 == 0:
                time = data.ReadU32("ReplayTime")
                has_time = True
            else:
                p_type ^= 0x10
                time = prev_packet.time  # done to make sure all packets have a time attached
            count_ += 1
            # print(out[0])
            # print(out[0]-((data.GetReadOffset()-start+7)>>3))
            v = Data(p_type, data.ReadBytes(end_index-BITS_TO_BYTES(data.GetReadOffset())), time, has_time)
            self.packets.append(v)
            v.id_ = index
            index += 1
            prev_packet = v
        self.match_length = prev_packet.get_time()
        # data.Flush()


    def parse(self, byte_types, header_data) -> list[Data]:
        for i in byte_types:
            if type(i) is int:
                pass
            else:
                return []
        if type(header_data) is not list:
            return []
        return_packets = []
        if byte_types == b"":
            byte_types = b"\x00\x10\x01\x11\x02\x12\x03\x13\x04\x14\x05\x15\x06\x16\x07\x17\x08\x18\x09\x19"  # all possible current bytes
        for i in self.packets:
            bitstream = i.get_bitstream()
            packet_type = i.p_type

            if packet_type in byte_types:
                if len(header_data) > 0:
                    for header in header_data:
                        if header == bitstream.ReadBits(len(header) * 8):
                            return_packets.append(i)
                            break  # prevent double appending of packets
                        bitstream.SetReadOffset(0)
                else:
                    return_packets.append(i)
        return return_packets

    def update_internal(self):
        buffer = bytearray()
        for packet in self.packets:
            if packet.include:
                buffer.extend(packet.get_packet_full())
        self.replay.zlib_data = buffer

    def build(self, path, compression=9):
        self.update_internal()
        self.replay.build(path, compression)

    def get_all_reflectables(self) -> list[Data, bytes]:
        payload = []
        for i in self.parse(b"\x04\x14", [b"\x02\x58\x2d\xf0", b"\x02\x58\xaa\xf0", b"\x02\x58\x36\xd1"]):
            # for i in self.parse(b"\x04\x14", [b"\x02\x58\xaa\xf0"]):
            bs = i.get_bitstream()
            bs.IgnoreBytes(2)
            t = bs.ReadBits(16)
            i.is_compressed = False
            if t == b"\xaa\xf0":
                payload.append([i, bs.ReadRemaining()])
                continue

            if bs.ReadU8() == 1:  # is zstd compressed
                i.is_compressed = True
                size_maybe = bs.ReadUleb()
                size2_maybe = bs.ReadUleb()
                payload.append([i, zstd.decompress(bs.ReadRemaining())])
            payload.append([i, bs.ReadRemaining()])
        return payload

    def get_all_construction_packets(self, parsed):
        """
        a function to get all the construction packets from the replay. a construction packet is a packet used to
        'construct' an entity. it should hold enough information to make a vehicle include ammunition, modules, and camo info.
        This can return data for parsed or unparsed packets. a parsed packet will at the most contain data for one vehicle.
        an unparsed packet can contain data for multiple vehicles.
        :param parsed: if True, will parse the raw packet into multiple smaller packets
        :return:
        parsed is True: [origin packet: Packet, [[entity_id: str, parsed packet: bytes], ...], ...]
        parsed is False: [origin packet: Packet, [raw packet: bytes], ...]
        """
        payload = []
        for i in self.parse(b"\x06\x16", [b"\x25", b"\x24"]):
            bitstream = i.get_bitstream()
            p_type = bitstream.ReadU8()
            lz4_out = bitstream.ReadRemaining()
            if lz4_out is not None:
                try:
                    if p_type == 0x25:
                        v = lz4.decompress(lz4_out, 0xFFFF)
                    else:
                        v = lz4_out
                    if not parsed:
                        payload.append([i, [v]])
                    else:
                        payload.append([i, self.decode_construction_packet(v)])
                except UnicodeDecodeError as e:
                    pass
        return payload

    def get_all_replication_packets(self, parsed):
        payload = []
        for i in self.parse(b"\x06\x16", [b"\x23", b"\x22"]):
            bitstream = i.get_bitstream()
            p_type = bitstream.ReadBits(8)[0]
            lz4_out = bitstream.ReadRemaining()
            if lz4_out is not None:
                try:
                    if p_type == 0x23:
                        v = lz4.decompress(lz4_out, 0xFFFF)
                    else:
                        v = lz4_out
                    if not parsed:
                        payload.append([i, [v]])
                    else:
                        payload.append([i, self.decode_construction_packet(v)])
                except UnicodeDecodeError as e:
                    pass
        return payload

    def get_tickets(self):
        payload = []
        for i, data in self.get_all_reflectables():
            for bts in self.decode_reflection_packet_ret(data):
                bs = BitStream(bts)
                b1 = bs.ReadBits(8)
                b2 = bs.ReadBits(8)
                if b2 == b"\x78":
                    meta_type = bs.ReadBits(32)
                    if meta_type in [b"\x07\x00\x01\x20", b"\x0B\x00\x02\x30"]:
                        ticket_count = bs.ReadBits(16)
                        payload.append([i, int.from_bytes(b1, byteorder="little"),
                                        int.from_bytes(ticket_count, byteorder="little")])
        return payload

    def get_battle_logs(self, kills=True, severe_damage=True, critical_damage=True, awards=True):
        types = []
        if kills:
            types.append(b"\x02\x58\x58\xf0")
        if severe_damage:
            types.append(b"\x02\x58\x57\xf1")
        if critical_damage:
            types.append(b"\x02\x58\x56\xf0")
        if awards:
            types.append(b"\x02\x58\x78\xf0")
        '''payload = {
            "kill" : []
        }'''
        payload = []
        for packet in self.parse(b"\x04\x14", types):
            payload.append(packet)
        return payload

        # print(next_dat, int.from_bytes(next_dat, byteorder="little"))

    @staticmethod
    def decode_construction_packet(uncompressed_raw: bytes):

        payload = []
        bitstream = BitStream(uncompressed_raw)
        written = bitstream.ReadBits(8, "entry_couunt")
        for i in range(int.from_bytes(written, "little") + 1):
            server_eid = get_server_eid(
                bitstream)
            blockSizeBytes = bitstream.ReadUleb("block_size") * 8
            startpos = bitstream.GetReadOffset()
            x = bitstream.ReadBits(blockSizeBytes, "block_data")
            payload.append([server_eid, x])
            bitstream.SetReadOffset(startpos + blockSizeBytes)
        return payload

    @staticmethod
    def decode_reflection_packet(uncompressed_raw: bytes):
        binary = BitStream(uncompressed_raw)
        count = int.from_bytes(binary.ReadBits(16), byteorder='little')
        start_indexes = []
        for i in range(count):
            size = int.from_bytes(binary.ReadBits(16, "size_of_block"), byteorder='little')

            start_index = binary.current_bit_index
            end_index = start_index + size * 8
            start_indexes.append((start_index, end_index))

            binary.current_bit_index = end_index

        return start_indexes

    @staticmethod
    def decode_reflection_packet_ret(uncompressed_raw: bytes):
        binary = BitStream(uncompressed_raw)
        count = int.from_bytes(binary.ReadBits(16), byteorder='little')
        start_indexes = []
        for i in range(count):
            size = int.from_bytes(binary.ReadBits(16, "size_of_block"), byteorder='little')

            start_index = binary.current_bit_index
            end_index = start_index + size * 8
            start_indexes.append(binary.ReadBits(size * 8))

            binary.current_bit_index = end_index

        return start_indexes