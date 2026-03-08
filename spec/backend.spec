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
        ('./../.venv/Lib/site-packages/faster_whisper', 'faster_whisper/'),
        ('./../.venv/Lib/site-packages/hf_xet', 'hf_xet/')
        ],
    hiddenimports=[
        'charset_normalizer', 'chardet',
        'requests', 'urllib3', 'certifi', 'idna',
        'openai', 'openai._client', 'openai.resources', 'openai.types',
        'httpx', 'httpx._transports', 'httpcore',
        'pydantic', 'pydantic.deprecated', 'pydantic._internal',
        'packaging', 'packaging.version', 'packaging.requirements',
        'google.genai', 'google.genai._api_client',
        'langchain_core', 'langchain_core.language_models',
        'langchain_openai', 'langchain_google_genai', 'langchain_ollama',
        'websockets', 'websockets.legacy', 'websockets.legacy.server',
        'sudachipy', 'sudachidict_core', 'sudachidict_full',
        'comtypes', 'pyautogui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas', 'matplotlib', 'PyQt5'],
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
