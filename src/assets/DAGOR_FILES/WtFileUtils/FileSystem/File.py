from abc import ABC, abstractmethod
import json


class _BaseFile(ABC):
    """
    Base class for a file in a Filesystem

    """
    def __init__(self, file_name):
        self.file_name = file_name

    @abstractmethod
    def get_data(self):
        pass

    @abstractmethod
    def get_data_disk(self):
        pass


class VROMFs_File(_BaseFile):
    """
    simple class to store a file name, the offset in the parent vromf, and the size in the parent vromf
    """

    def __init__(self, true_name, offset, size, VROMFs):
        if isinstance(true_name, str):
            self.true_name = true_name.split("/")
        else:
            self.true_name: list[str] = true_name  # path to file, ex:path1/path2/xyz.blk
        super().__init__(true_name[-1])
        self.offset = offset
        self.size = size
        self.VROMFs = VROMFs  # the vromf to do the lookup in

    def stats(self):
        return f"path: {self.file_name}, offset: {self.offset}, size: {self.size}"

    def get_data(self):
        return self.VROMFs.open_file(self)

    def get_data_disk(self):
        temp = self.VROMFs.open_file(self)
        if isinstance(temp, dict):
            temp = json.dumps(temp, indent=4, ensure_ascii=False).encode('utf-8')
        return temp

    def __eq__(self, other):
        if isinstance(other, str):
            return self.file_name == other
        if not isinstance(other, VROMFs_File):
            return False
        return self.file_name == other.file_name
