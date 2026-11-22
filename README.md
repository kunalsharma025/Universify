# Universify

A music player in Python, built as a college project by a 2nd-year B.Tech student.

It plays your own local songs and streams songs online, and shows the true quality of each local song — bit depth, sample rate and kbps — including flagging a file that says FLAC but is really a renamed MP3.

## What it does

- Local Vault: play FLAC, WAV, MP3, AAC and OGG from your own folders.
- True quality check: reads the real file headers with mutagen and shows bit depth, sample rate and kbps for each local song. Flags a file that says FLAC but is really a renamed MP3.
- Online Stream: search and play from YouTube Music first. If YouTube fails or blocks, it switches to JioSaavn, then Audius. Streaming only, no download.
- Synced lyrics that follow the song, favourites, charts (Top India, Top World, Indie, Trending, Spotify Top 50 India and Global), mini player, fullscreen Now Playing with Up Next.
- Cinema mode: plays videos fullscreen, like VLC, with subtitles.
- AI Studio: lyrics and mood/summary help, BPM from librosa.

## How to run it

1. Install Python 3.12 or 3.13 on Windows.
2. Install VLC from videolan.org (python-vlc needs the VLC app to play sound).
3. Install Deno (needed by yt-dlp for YouTube): `winget install DenoLand.Deno`, then close and reopen your terminal.
4. In the project folder, install the libraries:
   `pip install -r requirements.txt`
5. Run it:
   `python main.py`

To build the exe: double-click `build_exe.bat`. The exe appears in `dist\`. VLC must stay installed, the exe uses it to play sound.

## How to use it

- Local Vault: click Local Vault on the left, then Add Folder, pick the folder with your songs. Click a song to play it. Click the song name at the bottom to open Now Playing. The inspector shows the true bit depth, sample rate and kbps.
- Online Stream: click Online Stream, type a song name in the search box and press Enter. Click a result to play it. The top buttons open charts (Top India, Top World, Indie, Trending, Spotify Top 50).
- Now Playing: click the song name at the bottom. You get a big cover, the queue (Up Next), lyrics, and the play/pause/next/back buttons. Press F or the fullscreen button for fullscreen.
- Favourites: click the heart on a song to save it. Open Favourites from the left to see them.
- Mini player: click Mini at the bottom to shrink the app into a small floating bar. Click it again (or double-click it) to bring the full app back.
- Cinema: click Cinema on the left, then Add Folder, pick a folder with videos. Click a video to play it. The controls hide in fullscreen — press the small arrow to bring them back.

## How it works

- The window is made with PySide6. Sound and video are played by python-vlc, which uses the VLC app.
- Local quality: mutagen reads the real headers of the audio file (not the file name), so it reports the true bit depth, sample rate and kbps, and catches a renamed MP3 pretending to be FLAC.
- YouTube Music search uses ytmusicapi (unofficial). yt-dlp turns a video into a playable audio link. The app tries the TV, iOS and web clients, and falls back to JioSaavn and Audius when YouTube refuses a link.
- JioSaavn and Audius are free web APIs, no login and no key. JioSaavn gives 320kbps streams, Audius gives 128kbps.
- Lyrics come from LRCLIB, matched to the song title and artist. Mood uses Hugging Face CLAP, BPM uses librosa on local files.
- Covers are read from the song files themselves with mutagen. Online covers come from the search results.
- Your music folder, last played song and favourites are saved on your own computer only (library.json, last_played.json, favourites.json). They are never uploaded.

## Note

This was built while learning Python, step by step. YouTube search is unofficial and YouTube sometimes blocks it. That is why JioSaavn and Audius are there as fallbacks, so songs keep playing.
