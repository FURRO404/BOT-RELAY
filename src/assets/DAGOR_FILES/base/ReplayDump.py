if __name__ == '__main__':
    from ReplayOpener import Replay
else:
    from .ReplayOpener import Replay

import os
import json

def dump(PATH: str):
    rpl = Replay(PATH)
    if rpl.is_good:
        f_name = PATH.split('\\')[-1]
        os.mkdir(rf"replay_dumps/{f_name}")
        with open(f"replay_dumps/{f_name}/FOOTER.BLK", "w") as f:
            f.write(json.dumps(rpl.footer_blk))

        with open(f"replay_dumps/{f_name}/HEADER.BLK", "w") as f:
            f.write(json.dumps(rpl.header_blk))

        with open(f"replay_dumps/{f_name}/RAW.bin", "wb") as f:
            f.write(rpl.zlib_data)

path = "D:\SteamLibrary\steamapps\common\War Thunder\Replays\#2025.05.24 00.18.25.wrpl"
dump(path)