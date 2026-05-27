import os
import traceback
import re

from ..FileSystem.File import _BaseFile
from ..Exceptions import FileSystemException
from ..FileSystem.FileSystemQuery import FileSystemQuery, MassFileSystemQuery


# noinspection PyTypeChecker
class FSDirectory:
    """
    one of the classes apart of a file system.
    a virtual directory that can hold references to other directories or files
    a vromfs will generate or use one of these to store files
    :param name: the name of the directory
    :param parent: used in backtracing to help determine path to base. if its the first directory in the section
     then set it to None

    when using indexing / __getitem__ you can supply a string path and it will return the first directory or file (in that order)
    that matches. to search for only a file or directory, supply an additional argument of 1 (file) or
    2 (directory).
    examples: dir_inst["pathname"], dir_inst["pathname", 1]
    a invalid path will return none
    """
    def __init__(self, name, parent):
        self.name = name
        self.parent = parent

        """
        The files and directories are stored as dictionaries because it makes lookup and access easier, especially for directories
        """
        self._files: dict[_BaseFile] = {}
        self._directories: dict[FSDirectory] = {}

    def add_directory(self, name):
        """
        creates a directory of name and adds it to the current directory
        :param name:
        :return:
        """
        d = FSDirectory(name, self)
        self._directories.update({name: d})
        return d

    def fetch_or_add_directory(self):
        pass

    def add_file(self, file: _BaseFile | FileSystemQuery):
        """
        supplied with a file, will add it to the current directory

        if supplied with a FileSystemQuery, will navigate through the directories specified and place the file there
        """
        if isinstance(file, FileSystemQuery):
            if file.file_obj is None:
                raise FileSystemException("FileSystemQuery object missing required attached file (file_obj) object")
            type_, name = file.get_next()
            if type_ == 1:
                directory = self._directories.get(name)
                if directory is None:
                    self.add_directory(name).add_file(file)
                else:
                    directory.add_file(file)

            elif type_ == 2:
                out = self._files.get(name)
                if out is None:
                    self._files.update({name: file.file_obj})
                else:
                    raise FileSystemException("Tried to create a file that already exists")

        if isinstance(file, _BaseFile):
            out = self._files.get(file.file_name)
            if out is None:
                self._files.update({file.file_name: file})
            else:
                raise FileSystemException("Tried to create a file that already exists")

    #TODO: add support for regex and directory lookup.
    def search_for_file(self, file: FileSystemQuery, suppress_errors = False) -> _BaseFile:
        """
        :param file: a FileSystemQuery object. this class only uses FIleSystemQuery Objects to search for a file
        :param suppress_errors: used to supress any
        :return: the found file, and only if supress_errors is True, sometimes a None
        """
        if not isinstance(file, FileSystemQuery):# error suppression wont ever apply to this
            raise FileSystemException("Passed an invalid argument to search_file")
        type_, name = file.get_next()
        if type_ == 1:
            directory = self._directories.get(name)
            if directory is None and not suppress_errors:
                raise FileSystemException(f"search_file was asked to search an invalid directory with name {name} in {self.name}")
            elif directory is None:
                return None
            return directory.search_for_file(file)
        elif type_ == 2:
            out = self._files.get(name)
            if out is None and not suppress_errors:
                raise FileSystemException(f"Tried to find a file that doesnt exist in directory {self.name}")
            elif out is None:
                return None
            return out

    def search_for_files(self, query: MassFileSystemQuery, suppress_errors = False) -> list[tuple[list,_BaseFile]]:
        """

        :param query:
        :param suppress_errors:
        :return:
        """
        # if not isinstance(query, MassFileSystemQuery):# error suppression wont ever apply to this
        #     raise FileSystemException("Passed an invalid argument to search_for_files")

        file_names = []
        stack_trace = self.stack_trace()
        files = []
        for directory in self._directories.values():
            files.extend(directory.search_for_files(query, suppress_errors))
        if query.file_exclude != [None]:
            for name in self._files:
                do = True
                for exclusion in query.file_exclude:
                    if isinstance(exclusion, str):
                        if exclusion in name:
                            do = False
                            break
                    if isinstance(exclusion, re.Pattern):
                        if exclusion.match(name) is not None:
                            do = False
                            break
                if do:
                    file_names.append(name)
        else:
            file_names = self._files.keys()

        if query.file_include != [None]:
            for name in file_names:
                for inclusion in query.file_include:
                    if isinstance(inclusion, str):
                        if inclusion in name:
                            files.append((stack_trace+[name], self._files.get(name)))
                    if isinstance(inclusion, re.Pattern):
                        if inclusion.match(name) is not None:
                            files.append((stack_trace+[name], self._files.get(name)))
        else:
            for name in file_names:
                files.append((stack_trace+[name], self._files.get(name)))

        return files

    def dump(self, spacing=0):
        for f in self._files.values():
            print(" "*spacing, f.file_name)
        for d in self._directories.values():
            print(" "*spacing, d.name + ":")
            d.dump(spacing+2)


    def dump_files(self, base_dir, skip=False):
        '''
        this dumps all the files to the specified directory (base_dir)
        makes directories as needed

        :param base_dir: the literal directory to dump files to, as in a path in your OS filesystem
        :param skip: if you want to skip files already created or throw an exception
        :return: None
        '''
        for f in self._files.values():
            if skip:
                if os.path.exists(base_dir + "/" + f.file_name):
                    continue
            with open(base_dir + "/" + f.file_name, "x") as x:
                pass
            with open(base_dir + "/" + f.file_name, "wb") as x:
                try:
                    print(f"writing {'/'.join(f.true_name)} to disk")
                    x.write(f.get_data_disk())
                except Exception as e:
                    stack_trace = traceback.format_exc()
                    disk_trace = self.stack_trace()
                    print(f"ERROR WRITING FILE TO DISK: path: {f.file_name}")
                    print(disk_trace)
                    print("STACK TRACE: ")
                    print(stack_trace)
        for d in self._directories.values():
            try:
                os.mkdir(os.path.join(base_dir, d.name))
            except Exception as e:
                pass
            d.dump_files(os.path.join(base_dir, d.name), skip=skip)

    def get_all_file_paths(self):
        """
        returns a list of all the file paths stored in the Directory
        :return: list[str]
        """
        stack_t = self.stack_trace()
        files = []
        for directory in self._directories.values():
            files.extend(directory.get_all_file_paths())

        for f in self._files.values():
            files.append('/'.join(stack_t+[f.file_name]))
        return files

    def stack_trace(self):
        if self.parent is None:
            return [self.name]
        else:
            v = self.parent.stack_trace()
            v.append(self.name)
            return v

    def extend(self, directory): # FSDirectory
        """
        a method that extends the current FSDirectory with all the files from another directory
        preserves paths from Base
        :param directory: directory to pull files from
        :return:
        """


    def __getitem__(self, item):
        """

        when using indexing / __getitem__ you can supply a string path
        and it will return the first  file or directory (in that order) that matches.

        to search for only a file or directory, supply an additional argument of 1 (file) or 2 (directory).
        examples: dir_inst["pathname"], dir_inst["pathname", 1]
        a invalid path will return none
        :param item:
        :return: None, a _BaseFile, or a FSDirecory
        """
        if isinstance(item, tuple):
            if item[1] == 1:
                return self._files.get(item[0])
            elif item[1] == 2:
                return self._directories.get(item[0])
            else:
                raise Exception("Invalid argument, passed a value not of integer 1 or 2")

        payload = self._files.get(item)
        if payload is None:
            return self._directories.get(item)
        return payload
