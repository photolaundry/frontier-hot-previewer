import argparse
import os
import pathlib
import platform
import struct
import sys
import time

from wand.image import Image
from wand.display import display
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


# this block is used when run as a standalone .exe build by pyinstaller to help find IM
# dependencies are in a subdirectory when packaged with pyinstaller
if hasattr(sys, "_MEIPASS"):
    internal_dir = pathlib.Path(getattr(sys, "_MEIPASS"))
    default_config_file = internal_dir / pathlib.Path("cropall_default.ini")

    # ImageMagick directories
    os.environ["MAGICK_HOME"] = str(internal_dir)
    os.environ["MAGICK_CODER_FILTER_PATH"] = str(internal_dir / "modules/filters")
    os.environ["MAGICK_CODER_MODULE_PATH"] = str(internal_dir / "modules/coders")

    # Add the above paths PATH for wand/imagemagick on windows
    if sys.platform == "win32":
        os.environ["PATH"] += os.pathsep + os.environ["MAGICK_HOME"]
        os.environ["PATH"] += os.pathsep + os.environ["MAGICK_CODER_FILTER_PATH"]
        os.environ["PATH"] += os.pathsep + os.environ["MAGICK_CODER_MODULE_PATH"]


class FrontierScanFileHandler(PatternMatchingEventHandler):
    def __init__(self):
        PatternMatchingEventHandler.__init__(
            self, patterns=["*.RAW"], ignore_directories=True, case_sensitive=False
        )

    def on_any_event(self, event):
        print(f"found file {event.event_type}: {event.src_path}")

    def on_created(self, event):
        # Sometimes the file isn't quite ready to be read. The struct.unpack breaks
        # and doesn't get enough bytes from the read() so we wait a little bit
        time.sleep(1)
        with open(event.src_path, "rb") as img_raw:
            # read off the first 32 bytes for the header
            first_32_bytes = img_raw.read(32)
            if len(first_32_bytes) != 32:
                print("  Error reading the header for this image, skipping")
                return
            # <16H for little-endian unsigned short 16 times (2 bytes per msg)
            headers_bytes = struct.unpack("<16H", first_32_bytes)
            img_width, img_height = headers_bytes[4:6]
            print(f"height: {img_height} width: {img_width}")

            # rest of the img file is raw RGB data, feed into wand
            with Image(
                blob=img_raw,
                format="rgb",
                depth=8,
                interlace="no",
                height=img_height,
                width=img_width,
            ) as img:
                display(img)


def cli():
    watch_path = None
    if platform.system() == "Windows":
        watch_path = r"D:\Inspool"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        help=r"path to your Frontier PIC/export machine's Inspool folder (default D:\Inspool)",
        default=watch_path,
    )
    args = parser.parse_args()

    if not args.path:
        parser.error("No directory specified by --path!")

    handler = FrontierScanFileHandler()
    observer = Observer()
    observer.schedule(handler, args.path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    cli()
