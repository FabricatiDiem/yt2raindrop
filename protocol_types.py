from typing import Any, Mapping, Protocol


class HasExecute(Protocol):
    def execute(self) -> Mapping[str, Any]:
        ...


class HasListPaging(Protocol):
    def list(self, *args, **kwargs) -> HasExecute:
        ...

    def list_next(self, HasExecute, HasListPaging, *args, **kwargs) -> HasExecute:
        ...


class YoutubeService(Protocol):
    def videos(self) -> HasListPaging:
        ...

    def playlists(self) -> HasListPaging:
        ...

    def playlistItems(self) -> HasListPaging:
        ...
