# -*- mode: python ; coding: utf-8 -*-

# Reach into the privates of wand/api.py and grab the DLLs it finds
print("Find ImageMagick libraries")
libraries=[]
import os
import sys
import wand.api
from wand.api import library_paths
old_path = os.environ['PATH']
for libwand_path, libmagick_path in library_paths():
    if sys.platform != "win32" and (libwand_path or libmagick_path):
        print("Warning: searching hard coded path /lib64")
        libwand_path = os.path.join("/lib64", libwand_path) if libwand_path else None
        libmagick_path = os.path.join("/lib64", libmagick_path) if libmagick_path else None
    if libwand_path and os.path.exists(libwand_path):
        libraries += [(libwand_path, ".")]
    if libmagick_path and os.path.exists(libmagick_path):
        libraries += [(libmagick_path, ".")]
libraries = list(set(libraries))
path_extra = os.environ['PATH'][len(old_path):]
if sys.platform == "win32":
    for dir in set(path_extra.split(os.pathsep)):
        if "filters" in dir:
            for file in os.listdir(dir):
                libraries += [(os.path.join(dir, file), "modules/filters")]
        if "coders" in dir:
            for file in os.listdir(dir):
                libraries += [(os.path.join(dir, file), "modules/coders")]
else:
    import wand.version
    options = wand.version.configure_options()
    for file in os.listdir(options['FILTER_PATH']):
        libraries += [(os.path.join(options['FILTER_PATH'], file), "modules/filters")]
    for file in os.listdir(options['CODER_PATH']):
        libraries += [(os.path.join(options['CODER_PATH'], file), "modules/coders")]

for lib, dst in libraries:
    print(f"\tLibrary: {lib}")

a = Analysis(
    ['src\\frontier_hot_previewer\\__init__.py'],
    pathex=[],
    binaries=libraries,
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
    a.binaries,
    a.datas,
    [],
    name='frontier-hot-previewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
