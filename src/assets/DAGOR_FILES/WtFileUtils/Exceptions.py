class BlkParseException(Exception):
    pass

class BLKCriticalMissingException(Exception):
    def __init__(self, message):
        super().__init__(message)

class VROMFSException(Exception):
    pass

class FileSystemException(Exception):
    def __init__(self, message):
        super().__init__(message)