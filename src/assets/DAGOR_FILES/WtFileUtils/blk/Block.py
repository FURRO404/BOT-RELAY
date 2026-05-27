from ..blk.Chunk import Chunk


class Block:
    def __init__(self, name, param_count, blocks_count, first_block_id):
        self.name = name
        self.param_count = param_count
        self.blocks_count = blocks_count
        self.first_block_id = first_block_id
        self.children = []
        self.fields: list[Chunk] = []

    def get_basic(self) -> tuple:
        return self.name, self.param_count, self.blocks_count, self.first_block_id

    def add_field(self, chunk: Chunk):
        self.fields.append(chunk)

    '''
    function to convert data to more pythonic data type
    also used when converting blk to json as a python dict is basically a json
    
    works by recursively making a dictionary by adding parameters, then adding the children blocks dict to this dict.
    '''
    def to_dict(self) -> dict:
        payload = {}
        for f in self.fields:
            temp = {f.name: f.data}
            key = f.name
            if key in list(payload.keys()):
                if type(payload[key]) is not list:
                    payload[key] = [payload[key]]
                payload[key].append(temp[key])
            else:
                payload.update(temp)
        for f in self.children:
            temp = f.to_dict()
            key = list(temp.keys())[0]
            if key in list(payload.keys()):
                if type(payload[key]) is not list:
                    payload[key] = [payload[key]]
                payload[key].append(temp[key])
            else:
                payload.update(temp)
        return {self.name: payload}