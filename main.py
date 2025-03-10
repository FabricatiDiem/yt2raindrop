import json
import os
from itertools import chain
from time import sleep
from typing import Any, Iterable, Mapping, Optional

import click
import requests
from cytoolz.curried import filter, get
from cytoolz.functoolz import compose, do, excepts, pipe
from cytoolz.itertoolz import first
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from more_itertools import consume

from protocol_types import HasListPaging, YoutubeService

load_dotenv()

# Google OAuth Scopes
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Load credentials from file (replace with your credentials JSON file)
CREDENTIALS_FILE = os.environ["CREDENTIALS_FILE"]

# Raindrop.io API Token (Replace with your actual token)
RAINDROP_API_TOKEN = os.environ["RAINDROP_API_TOKEN"]


def get_youtube_service() -> YoutubeService:
    """Authenticates and returns a YouTube API service instance."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def list_key_items_from_pages(
    yt_obj: HasListPaging, key: str = "items", **kwargs
) -> Iterable[Mapping[str, Any]]:
    request = yt_obj.list(**kwargs)
    while request:
        response = request.execute()
        for item in response.get(key, []):
            yield item
        request = yt_obj.list_next(request, response)


def get_liked_videos(youtube: YoutubeService) -> Iterable[Mapping[str, str]]:
    """Fetches liked videos from YouTube."""
    yield from (
        {
            "title": item["snippet"]["title"],
            "url": f'https://www.youtube.com/watch?v={item["id"]}',
        }
        for item in list_key_items_from_pages(
            youtube.videos(), part="snippet", myRating="like", maxResults=50
        )
    )


def get_playlist_id(youtube: YoutubeService, playlist_name: str) -> Optional[str]:
    filter_playlist_matches = filter(
        lambda item: playlist_name == item["snippet"]["title"]
    )
    get_id_of_first = compose(
        get("id"), first
    )  # Note that this actually hides the possible StopIteration exception.
    id_or_none = excepts(StopIteration, get_id_of_first)

    return pipe(
        list_key_items_from_pages(
            youtube.playlists(), part="snippet", mine=True, maxResults=50
        ),
        filter_playlist_matches,
        id_or_none,
    )


def get_playlist_videos(
    youtube: YoutubeService, playlist_name: str
) -> Optional[Iterable[Mapping[str, Any]]]:
    """Fetches videos from the Watch Later playlist."""

    playlist_id = get_playlist_id(youtube, playlist_name)
    if not playlist_id:
        return None

    return (
        {
            "title": item["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}",
        }
        for item in list_key_items_from_pages(
            youtube.playlistItems(),
            part="snippet",
            playlistId=playlist_id,
            maxResults=50,
        )
    )


def add_to_raindrop(title: str, url: str) -> bool:
    """Adds a video to Raindrop.io bookmarks."""
    headers = {
        "Authorization": f"Bearer {RAINDROP_API_TOKEN}",
        "Content-Type": "application/json",
    }
    data = json.dumps(
        {"link": url, "title": title, "collection": {"$id": 0}}  # Default collection
    )

    response = requests.post(
        "https://api.raindrop.io/rest/v1/raindrop", headers=headers, data=data
    )
    return response.status_code == 200


def add_videos_to_raindrop(
    videos: Iterable[Mapping[str, str]], sleep_duration: float = 0.25
) -> None:
    def process_video(video: Mapping[str, str]) -> None:
        success = add_to_raindrop(video["title"], video["url"])
        print(f'{"✔" if success else "❌"} {video["title"]}')
        sleep(sleep_duration)

    consume(map(process_video, videos))


def save_video_info_to_file(
    video_list: Iterable[Mapping[str, Any]], outfile_name: str
) -> None:
    with open(outfile_name, "w") as outfile:
        outfile.write(json.dumps(video_list, indent=2))
        outfile.write("\n")


@click.command()
@click.option("--playlist-name", help="The name of the playlist to transfer.")
@click.option(
    "--liked", help="Whether to include liked videos.", is_flag=True, default=False
)
@click.option(
    "--save-to-file", help="Whether to save videos to file.", is_flag=True, default=True
)
@click.option(
    "--dry-run",
    help="Fetch info from Youtube but do not upload to Raindrop.io.",
    is_flag=True,
    default=False,
)
def main(
    playlist_name: Optional[str], liked: bool, save_to_file: bool, dry_run: bool
) -> None:
    youtube = get_youtube_service()

    if liked:
        liked_videos = list(get_liked_videos(youtube))
        print(f"Found {len(liked_videos)} liked videos.")
    else:
        liked_videos = []

    if playlist_name:
        _playlist_videos = get_playlist_videos(youtube, playlist_name)
        if _playlist_videos is None:
            print("Playlist not found.")
            playlist_videos = []
        else:
            playlist_videos = list(_playlist_videos)
            if not playlist_videos:
                print("Empty playlist.")
            else:
                print(
                    f"Found {len(playlist_videos)} videos in playlist `{playlist_name}`."
                )
    else:
        playlist_videos = []

    videos = list(chain(liked_videos, playlist_videos))

    if save_to_file:
        if liked:
            print("Saving liked videos to file.")
            save_video_info_to_file(liked_videos, "youtube_liked_videos.jsonl")
            print("Done saving liked videos to file.")

        if playlist_name:
            print(f"Saving playlist videos to file.")
            save_video_info_to_file(
                playlist_videos, f"youtube_playlist_{playlist_name}_videos.jsonl"
            )
            print("Done saving playlist videos to file.")

    if videos and not dry_run:
        print("Exporting videos to Raindrop.io bookmarks...")
        add_videos_to_raindrop(videos)
    else:
        print("No videos to export.")


if __name__ == "__main__":
    main()
