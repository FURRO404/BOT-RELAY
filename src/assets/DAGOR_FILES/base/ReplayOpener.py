import os
import zlib


from DAGOR_FILES.WtFileUtils.blk.BlkParser import BlkParser


class Replay:
    def __init__(self, path_to_file):
        self.is_good = False
        if not os.path.exists(path_to_file):
            print("Bad path")
            return
        print(path_to_file)
        self.path = path_to_file
        self.is_server = False
        with open(self.path, "rb") as f:
            bin = f.read()

            if len(bin) == 0:
                return
            self.header_dat = bytearray(bin[:0x000004CA])
            if bin[0x000004CA] == 0x78:
                self.is_server = True
            if not self.is_server:

                start_blk = BlkParser(bin, offset=0x000004CA)
                self.header_blk_bytes =start_blk.bytes_
            else:
                self.header_blk_bytes = b""

        if not self.is_server:
            self.header_blk = start_blk.to_dict()
            zlib_raw = start_blk.data.ReadRemaining()
        else:
            self.header_blk = {}
            zlib_raw = bin[0x000004CA:]

        d = zlib.decompressobj()
        self.zlib_data = d.decompress(zlib_raw)
        unused = d.unused_data
        if len(unused) > 0:
            footer = BlkParser(unused)
            self.footer_blk = footer.to_dict()
            self.footer_blk_bytes = footer.bytes_

        else:
            self.footer_blk = {}
            self.footer_blk_bytes = b""
        self.is_good = True

    def build(self, path, compression):
        inner_data = self.header_blk_bytes + zlib.compress(self.zlib_data, compression)

        z = len(inner_data) + len(self.header_dat)
        x = z.to_bytes(4, byteorder='little')
        for i in range(4):
            self.header_dat[0x000002AC+i] = x[i]

        with open(path, "wb") as f:
            f.write(self.header_dat+inner_data+self.footer_blk_bytes)
