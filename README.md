# YT2Raindrop

This is just a simple Python CLI to save Raindrop bookmarks from videos liked or saved to playlists on Youtube.

Note: Due to restrictions on the Youtube API, this cannot copy from one's Watch Later list, unfortunately.

## How to Use
You will need:
* Youtube API OAuth key (JSON)
* Raindrop.IO API key

Also, be sure to install the Poetry environment (see `pyproject.toml` and `poetry.lock`)

One can either define the following environment variables or define them in a .env file in the root:
* CREDENTIALS_FILE
  * Points to the full path of one's Youtube API OAuth key above
* RAINDROP_API_TOKEN
  * Has the user-specific Raindrop.IO API token

The CLI help page can be triggered as follows:

`poetry run python main.py --help`
