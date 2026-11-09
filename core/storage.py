from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    def __init__(self, **kwargs):
        super().__init__(location=settings.PRIVATE_MEDIA_ROOT, **kwargs)

    def deconstruct(self):
        return ("core.storage.PrivateMediaStorage", (), {})