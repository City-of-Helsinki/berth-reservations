class ProfileServiceException(BaseException):
    """Base exception for errors related to the Profile Service"""

    def __init__(self, msg=None, *args):
        super().__init__(msg or self.__doc__, *args)


class MultipleProfilesException(ProfileServiceException):
    """More than one profile found"""

    def __init__(self, ids, *args):
        self.ids = ids
        super().__init__(*args)


class NoProfilesException(ProfileServiceException):
    """No profiles found"""

    pass
