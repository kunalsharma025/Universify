# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
# Build with:  pyinstaller Universify.spec --clean --noconfirm
# Or just double-click build_exe.bat
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')] + collect_data_files('ytmusicapi'),
    hiddenimports=[
        'src', 'src.main_window', 'src.ai', 'src.config', 'src.cover',
        'src.inspector', 'src.library', 'src.online', 'src.player',
        'src.scanner', 'src.ui_controls', 'src.ui_pages',
        'src.ui_account', 'src.ui_online',
        'src.ui_telemetry', 'src.visualizer', 'src.mini_player',
        'src.ai_mixin', 'src.accounts',
        'src.video_mixin', 'src.fullscreen_mixin', 'src.favourites_mixin',
        'src.playback_mixin', 'src.tracks_mixin',
        'yt_dlp', 'yt_dlp.extractor', 'mutagen', 'mutagen.flac',
        'mutagen.mp3', 'mutagen.oggvorbis', 'mutagen.mp4',
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['librosa', 'numba', 'scipy', 'pandas', 'tensorflow', 'torch'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Universify',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets\\icon.ico',
)
