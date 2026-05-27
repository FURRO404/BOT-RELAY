from ..FileSystem.File import _BaseFile
from ..Exceptions import FileSystemException

class Path:
    def __init__(self, path: list[str] | str, dir_ptr = 0):
        if isinstance(path, list):
            self.path = path
        else:
            self.path = path.split("/")
        self.dir_ptr = dir_ptr

    def advance(self):
        if len(self.path) <= self.dir_ptr:
            pass
        if self.path[self.dir_ptr].endswith("\x00"):
            return
        self.dir_ptr += 1

    def fetch(self):
        if len(self.path) <= self.dir_ptr:
            pass
        if self.path[self.dir_ptr].endswith("\x00"):
            return self.path[self.dir_ptr][:-1]
        else:
            self.advance()
            return self.path[self.dir_ptr-1]


    def get(self):
        if len(self.path) <= self.dir_ptr:
            pass
        return self.path[self.dir_ptr]


class FileSystemQuery:
    """
    an object used to query a FileSystem / Directory for a specified file
    if supplied a file_obj (an object that inherits _BaseFile), it can also be used to add a file to a directory

    """
    def __init__(self, file, dir_ptr = 0, file_obj = None):
        if isinstance(file, list):
            *self.path, self.name = file
        else:
            *self.path, self.name = file.split('/')
        self.dir_ptr = dir_ptr # value used in file lookup to tell the Directory what path to use for lookup
        self.file_obj: _BaseFile = file_obj


    def get_next(self):
        """
        gets the current path of the query and advances dir_ptr by one
        returns 1, dir_name when supplied a directory
        returns 2, name when at file name
        """
        if self.dir_ptr > len(self.path):
            raise FileSystemException(f'Tried to access a higher level directory than applicable in current FileSystemQuery. Path: {self.path}; Name: {self.name}')
        if self.dir_ptr == len(self.path):
            self.dir_ptr += 1
            return 2, self.name
        else:
            self.dir_ptr += 1
            return 1, self.path[self.dir_ptr-1]


    def get_current(self):
        """
        same as get_next, but doesnt advance dir_ptr
        """
        if self.dir_ptr > len(self.path):
            raise FileSystemException(f'Tried to access a higher level directory than applicable in current FileSystemQuery. Path: {self.path}; Name: {self.name}')
        if self.dir_ptr == len(self.path):
            return 2, self.name
        else:
            return 1, self.path[self.dir_ptr-1]

class MassFileSystemQuery:
    """
    an object used to query a FileSystem / Directory for files

    any string inside a directory lookup that ends with a \x00 (aka null terminated)

    exclude operations will be checked first, then include on what was left
    :param dir_include: any directory that matches to the input will be included for file searching
    :param dir_exclude:
    :param file_name_include:
    :param file_exclude:
    """
    def __init__(self, dir_include, dir_exclude, file_include, file_exclude):
        if not isinstance(dir_include, list):
            self.dir_include = [dir_include]
        else:
            self.dir_include = dir_include

        if not isinstance(dir_exclude, list):
            self.dir_exclude = [dir_exclude]
        else:
            self.dir_exclude = dir_exclude

        if not isinstance(file_include, list):
            self.file_include = [file_include]
        else:
            self.file_include = file_include

        if not isinstance(file_exclude, list):
            self.file_exclude = [file_exclude]
        else:
            self.file_exclude = file_exclude
