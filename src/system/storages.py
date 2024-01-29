from django.conf import settings
from django.core.files.storage import FileSystemStorage


class CommonFileSystemStorage(FileSystemStorage):
    def __init__(
        self,
        location=None,
        base_url=None,
        file_permissions_mode=None,
        directory_permissions_mode=None,
    ):
        self._location = location or settings.STORAGE_ROOT
        self._base_url = base_url or settings.STORAGE_URL
        super().__init__(
            location=self._location,
            base_url=self._base_url,
            file_permissions_mode=file_permissions_mode,
            directory_permissions_mode=directory_permissions_mode,
        )


class StaticFileSystemStorage(FileSystemStorage):
    def __init__(
        self,
        location=None,
        base_url=None,
        file_permissions_mode=None,
        directory_permissions_mode=None,
    ):
        self._location = location or settings.STATIC_ROOT
        self._base_url = base_url or settings.STATIC_URL
        super().__init__(
            location=self._location,
            base_url=self._base_url,
            file_permissions_mode=file_permissions_mode,
            directory_permissions_mode=directory_permissions_mode,
        )


class MediaFileSystemStorage(FileSystemStorage):
    def __init__(
        self,
        location=None,
        base_url=None,
        file_permissions_mode=None,
        directory_permissions_mode=None,
    ):
        self._location = location or settings.MEDIA_ROOT
        self._base_url = base_url or settings.MEDIA_URL
        super().__init__(
            location=self._location,
            base_url=self._base_url,
            file_permissions_mode=file_permissions_mode,
            directory_permissions_mode=directory_permissions_mode,
        )
