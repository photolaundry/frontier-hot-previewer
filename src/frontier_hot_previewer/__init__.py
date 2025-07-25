import argparse
import os
import pathlib
import platform
import struct
import subprocess
import sys
import tempfile
import time

from wand.image import Image
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


# this block is used when run as a standalone .exe build by pyinstaller to help find IM
# dependencies are in a subdirectory when packaged with pyinstaller
if hasattr(sys, "_MEIPASS"):
    internal_dir = pathlib.Path(sys._MEIPASS)
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
    def __init__(self, tmpdir):
        PatternMatchingEventHandler.__init__(
            self, patterns=["*.RAW"], ignore_directories=True, case_sensitive=False
        )
        self.tmpdir = pathlib.Path(tmpdir)
        self.tmp_preview_filepath = self.tmpdir / "hot-preview.tif"

    def on_any_event(self, event):
        print(f"file {event.event_type}: {event.src_path}")

    def on_created(self, event):
        # Sometimes the file isn't quite ready to be read. The struct.unpack breaks
        # and doesn't get enough bytes from the read() so we wait a little bit
        time.sleep(1)
        with open(event.src_path, "rb") as img_raw:
            # read off the first 32 bytes for the header
            first_32_bytes = img_raw.read(32)
            if len(first_32_bytes) != 32:
                print("Error reading the header for this image, skipping")
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
                img.format = "tif"
                img.save(filename=self.tmp_preview_filepath)
        self.open_image()

    def open_image(self):
        open_command = ""
        sys = platform.system()
        if sys == "Darwin":
            open_command = "open"
        elif sys == "Linux":
            open_command = "xdg-open"
        elif sys == "Windows":
            open_command = "start"
        else:
            raise ValueError("Couldn't determine the OS!")
        try:
            subprocess.run(
                [open_command, str(self.tmp_preview_filepath)], check=True, shell=True
            )
        except subprocess.CalledProcessError as err:
            print("  Error while viewing image:")
            print(err.stdout)
            print(err.stderr)


def cli():
    watch_path = None
    if platform.system() == "Windows":
        watch_path = r"D:\Inspool"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        help="path to your Frontier PIC/export machine's D drive",
        default=watch_path,
    )
    args = parser.parse_args()

    if not args.path:
        print("No directory specified by --path!")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        handler = FrontierScanFileHandler(tmpdir)
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
