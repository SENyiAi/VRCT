# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\src-python\\mainloop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('./../src-python/models/overlay/fonts', 'fonts/'),
        ('./../src-python/models/translation/translation_settings/prompt', 'translation_settings/prompt/'),
        ('./../src-python/models/translation/translation_settings/languages', 'translation_settings/languages/'),
        ('./../.venv/Lib/site-packages/zeroconf', 'zeroconf/'),
        ('./../.venv/Lib/site-packages/openvr', 'openvr/'),
        ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas', 'matplotlib', 'PyQt5', 'torch', 'ctranslate2', 'transformers', 'faster_whisper', 'whisper', 'sentencepiece'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VRCT-sidecar-x86_64-pc-windows-msvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='.',
)
