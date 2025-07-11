import argparse
import platform
import struct
import subprocess
import tempfile
import time

from pathlib import Path

from wand.image import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FrontierScanFileHandler(FileSystemEventHandler):

    def __init__(self, tmpdir):
        self.tmpdir = Path(tmpdir)
        self.tmp_preview_filepath = self.tmpdir / "hot-preview.tif"

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        if file_path.suffix != ".RAW":
            return
        with open(file_path, "rb") as img_raw:
            # read off the first 32 bytes for the header
            first_32_bytes = img_raw.read(32)
            # <H for little-endian unsigned short (2 bytes per msg)
            headers_bytes = struct.unpack("<HHHHHHHHHHHHHHHH", first_32_bytes)
            img_height, img_width = headers_bytes[4:6]
            print(f"height: {img_height} width: {img_width}")

            # rest of the img file is raw RGB data, feed into wand
            with Image(blob=img_raw, format="rgb", depth=8, interlace="no", height=img_height, width=img_width) as img:
                img.format = "tif"
                img.save(filename=self.tmp_preview_filepath)
        self.open_image()

    def open_image(self):
        open_command = ""
        match platform.system():
            case "Darwin":
                open_command = "open"
            case "Linux":
                open_command = "xdg-open"
            case "Windows":
                open_command = "start"
            case _:
                raise ValueError("Couldn't determine the OS!")
        try:
            subprocess.run(
                [open_command, str(self.tmp_preview_filepath)],
                check=True
            )
        except subprocess.CalledProcessError as err:
            print("  Error while viewing image:")
            print(err.stdout)
            print(err.stderr)

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "d_drive_path",
        help="path to your Frontier PIC/export machine's D drive"
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        handler = FrontierScanFileHandler(tmpdir)
        observer = Observer()
        observer.schedule(handler, args.d_drive_path, recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


if __name__ == "__main__":
    cli()
