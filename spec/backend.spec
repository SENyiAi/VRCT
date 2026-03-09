# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# charset_normalizer has C extensions that hiddenimports alone won't bundle.
# collect_all ensures .pyd/.dll files, data files, and submodules are all included.
_cn_datas, _cn_binaries, _cn_hiddenimports = collect_all('charset_normalizer')
_cd_datas, _cd_binaries, _cd_hiddenimports = collect_all('chardet')

a = Analysis(
    ['..\\src-python\\mainloop.py'],
    pathex=[],
    binaries=[] + _cn_binaries + _cd_binaries,
    datas=[
        ('./../src-python/models/overlay/fonts', 'fonts/'),
        ('./../src-python/models/translation/translation_settings/prompt', 'translation_settings/prompt/'),
        ('./../src-python/models/translation/translation_settings/languages', 'translation_settings/languages/'),
        ('./../.venv/Lib/site-packages/zeroconf', 'zeroconf/'),
        ('./../.venv/Lib/site-packages/openvr', 'openvr/'),
        ('./../.venv/Lib/site-packages/faster_whisper', 'faster_whisper/'),
        ('./../.venv/Lib/site-packages/hf_xet', 'hf_xet/')
        ] + _cn_datas + _cd_datas,
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
    ] + _cn_hiddenimports + _cd_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas', 'matplotlib', 'PyQt5', 'tkinter', 'unittest',
        'pip', 'pkg_resources._vendor', 'distutils',
        # torch submodules not needed by VRCT — excluding them significantly
        # reduces both Analysis time (10-15min) and output size (~100MB)
        'torch.distributed', 'torch.testing', 'torch.utils.tensorboard',
        'torch.utils.benchmark', 'torch.utils.bottleneck', 'torch.utils.data',
        'torch.ao', 'torch.onnx', 'torch.optim', 'torch.autograd',
        'torch.jit', 'torch.fx', 'torch.export', 'torch.compiler',
        'torch.profiler', 'torch.sparse', 'torch.nested',
        'torch.package', 'torch.hub', 'torch.nn.parallel',
        'torch._dynamo', 'torch._inductor', 'torch._functorch',
        'torch.multiprocessing', 'torch.backends.cudnn',
        'torch.cuda.amp', 'torch.cuda.profiler', 'torch.cuda.nvtx',
        'torch.utils.cpp_extension', 'torch.utils.mobile_optimizer',
        'torch.utils.mkldnn', 'torch.quantization',
        'torch.nn.quantized', 'torch.nn.intrinsic',
        'torch.nn.qat',
        # Large unused transitive dependencies
        'triton', 'sympy', 'networkx',
        'torch.library', 'torch._refs', 'torch._prims',
        'torch._subclasses', 'torch._higher_order_ops',
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
