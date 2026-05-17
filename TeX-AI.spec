# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['TeX-AI.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TeX-AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,   # <--- SỬA THÀNH TRUE Ở ĐÂY
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['TeX-AI.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TeX-AI',
)

app = BUNDLE(
    coll,                   # <--- SỬA CHỮ 'exe' THÀNH 'coll' Ở ĐÂY
    name='TeX-AI.app',
    icon='TeX-AI.icns',
    bundle_identifier='com.tuan.tex-ai',
    info_plist={
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'LaTeX Document',
                'CFBundleTypeExtensions': ['tex'],
                'CFBundleTypeIconFile': 'TeX-AI.icns',
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
                'LSItemContentTypes': ['public.tex', 'org.tug.tex']
            }
        ],
        'NSHighResolutionCapable': True,
        'NSPrincipalClass': 'NSApplication',
    },
)
