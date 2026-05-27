# from BlkTypes import BlkTypes
from typing import Union

from ..blk.ParamParser import BLKTypes
import dataclasses


@dataclasses.dataclass
class Chunk:
    name: str
    data_type_raw: int
    data_type: str
    data_raw: bytes
    data: Union[int, list[int], float, list[float], bool, str, dict]


class ChunkParser:
    """
    a helper class that stores a converter and a name map.
    stores relevant information that could later on be used to generate true blk files, currently only
    name and data are actually used.
    """

    def __init__(self, name_map: list[str], converter: BLKTypes):
        self.name_map = name_map
        self.converter = converter

    def parse(self, data: bytes) -> Chunk:

        name_raw = data[0:3]
        name = self.name_map[int.from_bytes(name_raw, 'little')]
        data_type_raw = data[3]
        data_type: str = BLKTypes.types[data_type_raw]
        data_raw = data[4:]
        data = self.converter.fromRawParamInfo(data_type_raw, data_raw)
        return Chunk(name, data_type_raw, data_type, data_raw, data)