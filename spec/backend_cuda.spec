# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\src-python\\mainloop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('./../src-python/models/overlay/fonts', 'fonts/'),
        ('./../src-python/models/translation/translation_settings/prompt', 'translation_settings/prompt/'),
        ('./../src-python/models/translation/translation_settings/languages', 'translation_settings/languages/'),
        ('./../.venv_cuda/Lib/site-packages/zeroconf', 'zeroconf/'),
        ('./../.venv_cuda/Lib/site-packages/openvr', 'openvr/'),
        ('./../.venv_cuda/Lib/site-packages/faster_whisper', 'faster_whisper/'),
        ('./../.venv_cuda/Lib/site-packages/hf_xet', 'hf_xet/')
        ],
    hiddenimports=['charset_normalizer', 'chardet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas', 'matplotlib', 'PyQt5',
        'torch.testing', 'torch.utils.benchmark', 'torch.utils.tensorboard',
        'IPython', 'PIL.ImageQt', 'tkinter', 'wx',
    ],
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
    upx=False,  # UPX on CUDA DLLs takes 20-30min with minimal gain
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
    upx=False,  # UPX on CUDA DLLs takes 20-30min with minimal gain
    upx_exclude=[],
    name='.',
)
