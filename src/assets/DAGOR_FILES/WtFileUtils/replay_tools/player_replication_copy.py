from DAGOR_FILES.WtFileUtils.BitStream import BitStream
import zstandard as zstd

# with open("zlib.out", "rb") as f:
#     bs = BitStream(f.read(), do_im_hex=False)


ENTITY_INDEX_BITS = 22




def make_eid(index, gen):
    return index | (gen << ENTITY_INDEX_BITS)


# inp_bytes is 4 bytes
def get_server_eid(bitstream: BitStream, v=""):
    temp_ = bitstream.ReadBits(16, f"server_eid_first_half_{v}")
    first16_bit = int.from_bytes(temp_, "little")
    # print("first 16 bits", first16Bit, temp_)
    if first16_bit & 1:  # 2 byte version
        return make_eid(first16_bit >> 2, (first16_bit & 2) >> 1)
    elif first16_bit & 2:  # short eid: 3 byte version
        raise Exception
    else:  # long eid, 4 byte version
        raise Exception

def uid(bs_):
    return bs_.ReadBits(0x248, "uid_player")


def invitedNickName(bs_: BitStream, v="Nickname"):
    try:
        return bs_.ReadBits(bs_.ReadUleb(v+"_len")*8, v).decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        return ""


def nickLocKey(bs_):
    return invitedNickName(bs_,"nickLocKey") #idk?????


def clanTag(bs_):
    return invitedNickName(bs_, "clantag") # makes sense I guess


def title(bs_):
    return invitedNickName(bs_, "title")


def publicFlags(bs_, v="publicFlags"):
    return bs_.ReadBits(0x20, v) # I pray to gods that this doesnt change, based on length of varMeta
    # bs_.ReadBits(0x20) # only if ->flags & 0x820 is the same (wish)
    # bs_.ReadBits(0x20) #always happens


def decals(bs_):
    bs_.ReadUleb("blksize") # actually doing a BLK call here I think


def team(bs_):
    return bs_.ReadBits(8, "team")


def countryId(bs_):
    return bs_.ReadBits(8, "CountryId")


def memberId(bs_, v="MemberId"):
    return bs_.ReadBits(16, v)


def customState(bs_):
    return bs_.ReadUleb("customState_blk_uleb")


def score(bs_):
    return memberId(bs_, "score") # I HAVE NO FUCKING IDEA BUT GAIJIN GODS HAVE SPOKEN


def dummyForSupportPlanes(bs_):
    bs_.ReadBits(0x10, "dummyForSupportPlanes")

    bs_.ReadBits(0x10*5, "dummyForSupportPlanes")
    bs_.ReadBits(0x10*5, "dummyForSupportPlanes")
    bs_.ReadBits(0x10*5, "dummyForSupportPlanes")
    bs_.ReadBits(0x10*4, "dummyForSupportPlanes")



def pilotId(bs_):
    return publicFlags(bs_, "PilotId")


def disabledByMatchingSlots(bs_):
    return publicFlags(bs_, "disabledByMatchingSlots")


def brokenSlots(bs_):
    return publicFlags(bs_, "brokenSlots")


def wasReadySlots(bs_):
    return publicFlags(bs_, "wasReadySlots")


def spareAircraftInSlots(bs_):
    return publicFlags(bs_, "spareAircraftInSlots")


def ownedSlots(bs_):
    return publicFlags(bs_, "ownedSlots")


def classinessMark(bs_):
    return bs_.ReadBits(8, "classinessMark")


def timeToRespawn(bs_):
    return bs_.ReadBits(8*4, "timeToRespawn") # this function in ghidra is fucked, also FUCK FLAGS


def timeToRespawnInCoop(bs_):
    bs_.ReadBits(8*4, "timeToRespawnInCoop") # calls same function as @timeToRespawn


def forcedRespawn(bs_, v="forcedRespawn"):
    return bs_.ReadBits(1, f"{v}1bit") # WHYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY


def timeToKick(bs_):
    bs_.ReadBits(8*4, "timeToKick") # calls same function as @timeToRespawn


def guiState(bs_):
    classinessMark(bs_)


def spectatedModelIndex(bs_):
    publicFlags(bs_, "spectatedModelIndex")


def dummyForCountUsedSlots(bs_):
    return bs_.ReadBits(bs_.ReadBits(8, "dummyForCountUsedSlots_size")[0]*8, "dummyForCountUsedSlots")


def dummyForSpawnCosts(bs_):
    return bs_.ReadBits(bs_.ReadBits(8, "dummyForSpawnCosts_size")[0]*0x20, "dummyForSpawnCosts")


def dummyForSpawnDelayTimes(bs_):
    return bs_.ReadBits(bs_.ReadBits(8, "dummyForSpawnDelayTimes_size")[0]*0x10, "dummyForSpawnDelayTimes")


def dummyForKillStreaksProgress(bs_: BitStream):
    size_ = bs_.ReadBits(8, "dummyForKillStreaksProgress_size")[0]
    for i in range(size_):
        bs_.ReadBits(8, "dummyForKillStreaksProgress")
        bs_.SetReadOffset(bs_.GetReadOffset()+2)

def state(bs_):
    return bs_.ReadBits(0x10, "state")


def squadScore(bs_):
    return publicFlags(bs_, "squadScore")


def ownedUnitRef(bs_, v="ownedUnitRef"):
    return get_server_eid(bs_, v)


def controlledUnitRef(bs_):
    return ownedUnitRef(bs_, "controlledUnitRef")


def supportUnitId(bs_):
    return memberId(bs_, "supportUnitId")


def wreckedPartShipUnitId(bs_):
    return memberId(bs_, "wreckedPartShipUnitId")


def dummyForRoundScore(bs_):
    bs_.ReadBits(0x20, "dummyForRoundScore")
    z_ = int.from_bytes(bs_.ReadBits(8, "dummyForRoundScore_len"))
    for i in range(z_):

        bs_.ReadBits(0x20, "dummyForRoundScore")


def roundKills(bs_):
    return memberId(bs_, "roundKills")


def roundFriendlyKills(bs_):
    return memberId(bs_, "roundFriendlyKills")


def roundDeaths(bs_):
    return memberId(bs_, "roundDeaths")


def roundGroundKills(bs_):
    return memberId(bs_, "roundGroundKills")


def roundNavalKills(bs_):
    return memberId(bs_, "roundNavalKills")


def roundAiKills(bs_):
    return memberId(bs_, "roundAiKills")


def roundAiGroundKills(bs_):
    return memberId(bs_, "roundAiGroundKills")


def roundAiNavalKills(bs_):
    return memberId(bs_, "roundAiNavalKills")


def dummyForPlayerStat(bs_):
    bs_.ReadBits(0x10, f"dummyForPlayerStat1")
    bs_.ReadBits(0x10, f"dummyForPlayerStat2")
    bs_.ReadBits(0x10, f"dummyForPlayerStat3")
    bs_.ReadBits(0x20, f"dummyForPlayerStat4l")
    bs_.ReadBits(0x20, f"dummyForPlayerStat5l")
    bs_.ReadBits(0x10, f"dummyForPlayerStat6")
    bs_.ReadBits(0x10, f"dummyForPlayerStat7")
    bs_.ReadBits(0x10, f"dummyForPlayerStat8")
    bs_.ReadBits(0x10, f"dummyForPlayerStat9")
    bs_.ReadBits(0x20, f"dummyForPlayerStat10l")
    bs_.ReadBits(0x10, f"dummyForPlayerStat11")
    bs_.ReadBits(0x10, f"dummyForPlayerStat12")
    bs_.ReadBits(0x10, f"dummyForPlayerStat13")


def dummyForFootballStat(bs_):
    bs_.ReadBits(0x10, f"dummyForFootballStat1")
    bs_.ReadBits(0x10, f"dummyForFootballStat2")
    bs_.ReadBits(0x10, f"dummyForFootballStat3")


def realNick(bs_):
    invitedNickName(bs_, "realNick")


def squadronId(bs_):
    return publicFlags(bs_, "squadronId")


def forceLockTarget(bs_):
    return bs_.ReadBits(0x10, "forceLockTarget")


def cachedIsAutoSquad(bs_):
    return forcedRespawn(bs_, "cachedIsAutoSquad")


def xuid(bs_):
    return bs_.ReadBits(0x40, "xuid")


def nickFrame(bs_):
    invitedNickName(bs_, "nickFrame")


def missionSupportUnitId(bs_):
    return memberId(bs_, "missionSupportUnitId")


def rageTokens(bs_):
    return memberId(bs_, "rageTokens")

class Player:
    @staticmethod
    def nullTerminate(bytes_):
        index = 0
        for b in bytes_:
            if b != 00:
                index += 1
            else:
                break
        return bytes_[:index].decode("utf-8", errors="ignore")

    def __init__(self, bs_player, pid):
        self.air_kills = None
        self.ground_kills = None
        self.assists = None
        self.deaths = None
        self.captures = None
        self.score = None
        self.pid = pid
        self.player_id_text = b""
        self.first_four_random_ass_bits = bs_player.ReadBits(32, "weird_data")
        # print(first_four_random_ass_bits.hex())
        player_uid = uid(bs_player)
        self.player_global_id = int.from_bytes(player_uid[0:4], byteorder="little")
        self.some_data = player_uid[4:8]
        self.player_name = self.nullTerminate(player_uid[8:])
        self.invitedNickName= invitedNickName(bs_player)
        nickLocKey(bs_player)
        self.clanTag = clanTag(bs_player)
        self.title = title(bs_player)
        self.flags = publicFlags(bs_player)
        decals(bs_player)
        self.team = team(bs_player)[0]
        # print(self.player_global_id, self.player_name, self.clanTag, self.team)
        self.country = countryId(bs_player)
        self.memberId = memberId(bs_player)
        self.customState = customState(bs_player)
        self.score = score(bs_player)
        # print(self.score)
        self.dummyForSupportPlanes = dummyForSupportPlanes(bs_player)
        self.pilotId = pilotId(bs_player)
        # print(self.pilotId)
        self.disabledByMatchingSlots = disabledByMatchingSlots(bs_player)
        self.brokenSlots = brokenSlots(bs_player)
        self.wasReadySlots = wasReadySlots(bs_player)
        self.spareAircraftInSlots = spareAircraftInSlots(bs_player)
        self.ownedSlots = ownedSlots(bs_player)
        self.classinessMark = classinessMark(bs_player)
        self.timeToRespawn = timeToRespawn(bs_player)
        self.timeToRespawnInCoop = timeToRespawnInCoop(bs_player)
        self.forcedRespawn = forcedRespawn(bs_player)
        self.timeToKick = timeToKick(bs_player)
        self.guiState = guiState(bs_player)
        self.spectatedModelIndex =spectatedModelIndex(bs_player)
        self.dummyForCountUsedSlots = dummyForCountUsedSlots(bs_player)
        self.dummyForSpawnCosts = dummyForSpawnCosts(bs_player)
        self.dummyForSpawnDelayTimes = dummyForSpawnDelayTimes(bs_player)
        self.dummyForKillStreaksProgress = dummyForKillStreaksProgress(bs_player)
        self.state = state(bs_player)
        self.squadScore = squadScore(bs_player)
        # print(self.squadScore)

        self.uid = None
        self.vehicle = ""
        return
        self.ownedUnitRef = ownedUnitRef(bs_player)
        # print(hex(self.ownedUnitRef))
        self.controlledUnitRef = controlledUnitRef(bs_player)
        # print(self.controlledUnitRef)
        self.supportUnitId = supportUnitId(bs_player)
        self.wreckedPartShipUnitId = wreckedPartShipUnitId(bs_player)
        self.dummyForRoundScore = dummyForRoundScore(bs_player)
        self.roundKills = roundKills(bs_player)
        self.roundFriendlyKills = roundFriendlyKills(bs_player)
        self.roundDeaths = roundDeaths(bs_player)
        self.roundGroundKills = roundGroundKills(bs_player)
        self.roundNavalKills = roundNavalKills(bs_player)
        self.roundAiKills = roundAiKills(bs_player)
        self.roundAiGroundKills = roundAiGroundKills(bs_player)
        self.roundAiNavalKills = roundAiNavalKills(bs_player)
        # print(self.roundKills)
        self.dummyForPlayerStat = dummyForPlayerStat(bs_player)
        self.dummyForFootballStat = dummyForFootballStat(bs_player)
        self.realNick = realNick(bs_player)
        z = squadronId(bs_player)
        # print(z.hex())
        # print(z.hex())
        self.forceLockTarget = forceLockTarget(bs_player)
        self.cachedIsAutoSquad = cachedIsAutoSquad(bs_player)
        self.xuid = xuid(bs_player)
        self.nickFrame = nickFrame(bs_player)
        self.missionSupportUnitId = missionSupportUnitId(bs_player)
        # print(self.missionSupportUnitId.hex())
        self.rageTokens = rageTokens(bs_player)
        # print(self.forceLockTarget.hex())

    def __str__(self):
        # #return f"{self.id:<2}, {self.uid}, {self.team_id}, {self.player_id:<10}, {nullTerminate(self.name):<20}, {self.squadron_tag.decode("utf-8", errors="ignore")}, {self.vehicle.decode("utf-8", errors="ignore")}"
        return (f"{self.player_id_text[0:-1].decode('utf-8')}, {self.pid:<2}, {self.uid if self.uid is not None else '':<2}, {self.team:<1}, {self.player_global_id:<10}, {self.player_name:<20}, {self.clanTag if len(self.clanTag) > 0 else 'NA':<6}, {self.vehicle}, ")

    

def decode_zstd(binary: BitStream):
    count = int.from_bytes(binary.ReadBits(16), byteorder='little')
    players = []
    for i in range(count):
        size = int.from_bytes(binary.ReadBits(16, "size_of_block"), byteorder='little')

        start_index = binary.GetReadOffset()
        end_index = start_index + size*8
        if size < 100:
            binary.SetReadOffset(end_index)
            continue
        pid = binary.ReadBits(8)[0]
        if pid in range(255) and binary.ReadBits(8)[0] == 0x70:
            # print(binary.ReadBits(size*8))
            players.append(Player(binary, pid))
        binary.SetReadOffset(end_index)
    return players

'''for f1, f2 in sorted(bitscount.items()):
    continue
    print(hex(f1), f2)'''
