from DAGOR_FILES.ext.mpi import *
maybe_player_eid = 0
min_eid = 0x19
eid_list = []

def ext_uid_dispatch(oid: ObjectID, ext: ObjectExtUID, add_to_que: bool):
    object_oid = oid >> 0xb
    if ext == INVALID_OBJECT_EXT_UID:
        assert False, f"extended mpi uid is not set for object of type {oid}"
        return None
    ext_ = ((ext & 0xFF) << 16) | (ext >> 8)
    eid_val = ext >> 0x8
    eid_type = ext & 0xFF
    uVar8 = eid_list[eid_val][0:2]
    if maybe_player_eid == ext_ or min_eid <= eid_val or eid_list[eid_val][3] != ext_ >> 0x16 or uVar8 == 0xFFFF:
        if add_to_que:
            return None # here return object to do mpi que
        return None

