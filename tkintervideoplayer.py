import gc
import av
import time
import threading
import tkinter as tk
from PIL import ImageTk, Image, ImageOps
from typing import Tuple, Dict

class TkinterVideo(tk.Label):
    def __init__(self, master, scaled: bool = True, consistant_frame_rate: bool = True, keep_aspect: bool = False, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.path = ""
        self._load_thread = None
        self._paused = True
        self._stop = True
        self.consistant_frame_rate = consistant_frame_rate
        self._container = None
        self._current_img = None
        self._frame_number = 0
        self._time_stamp = 0
        self._current_frame_size = (0, 0)
        self._seek = False
        self._seek_sec = 0.0
        self._video_info = {"duration": 0, "framerate": 0, "framesize": (0, 0)}
        self.set_scaled(scaled)
        self._keep_aspect_ratio = keep_aspect
        self._resampling_method: int = Image.NEAREST
        self.bind("<<Destroy>>", self.stop)
        self.bind("<<FrameGenerated>>", self._display_frame)

    def keep_aspect(self, keep_aspect: bool):
        self._keep_aspect_ratio = keep_aspect

    def set_resampling_method(self, method: int):
        self._resampling_method = method

    def set_size(self, size: Tuple[int, int], keep_aspect: bool = False):
        self.set_scaled(False, self._keep_aspect_ratio)
        self._current_frame_size = size
        self._keep_aspect_ratio = keep_aspect

    def _resize_event(self, event):
        self._current_frame_size = (event.width, event.height)
        if self._paused and self._current_img and self.scaled:
            if self._keep_aspect_ratio:
                proxy_img = ImageOps.contain(self._current_img.copy(), self._current_frame_size)
            else:
                proxy_img = self._current_img.copy().resize(self._current_frame_size, self._resampling_method)
            self._current_imgtk = ImageTk.PhotoImage(proxy_img)
            self.config(image=self._current_imgtk)

    def set_scaled(self, scaled: bool, keep_aspect: bool = False):
        self.scaled = scaled
        self._keep_aspect_ratio = keep_aspect
        if scaled:
            self.bind("<Configure>", self._resize_event)
        else:
            self.unbind("<Configure>")
            self._current_frame_size = self.video_info()["framesize"]

    def _set_frame_size(self, event=None):
        self._video_info["framesize"] = (
            self._container.streams.video[0].width,
            self._container.streams.video[0].height
        )
        placeholder = Image.new("RGBA", self._video_info["framesize"], (255, 0, 0, 0))
        self.current_imgtk = ImageTk.PhotoImage(placeholder)
        self.config(width=150, height=100, image=self.current_imgtk)

    def _load(self, path):
        current_thread = threading.current_thread()
        try:
            with av.open(path) as self._container:
                stream = self._container.streams.video[0]
                stream.thread_type = "AUTO"
                try:
                    self._video_info["framerate"] = int(stream.average_rate)
                except TypeError:
                    raise TypeError("Not a video file")
                try:
                    self._video_info["duration"] = float(stream.duration * stream.time_base)
                    self.event_generate("<<Duration>>")
                except (TypeError, tk.TclError):
                    pass

                self._frame_number = 0
                self._set_frame_size()
                self.stream_base = stream.time_base

                try:
                    self.event_generate("<<Loaded>>")
                except tk.TclError:
                    pass

                now = time.time_ns() // 1_000_000  # current time in ms
                then = now
                time_per_frame = (1 / 30) * 1000

                while self._load_thread == current_thread and not self._stop:
                    if self._seek:
                        self._container.seek(int(self._seek_sec * 1_000_000), backward=True, any_frame=False)
                        self._seek = False
                        self._frame_number = int(self._video_info["framerate"] * self._seek_sec)
                        self._seek_sec = 0.0

                    if self._paused:
                        time.sleep(0.0001)
                        continue

                    now = time.time_ns() // 1_000_000
                    delta = now - then
                    then = now

                    try:
                        frame = next(self._container.decode(video=0))
                        self._time_stamp = float(frame.pts * stream.time_base)
                        width, height = self._current_frame_size
                        if self._keep_aspect_ratio:
                            im_ratio = frame.width / frame.height
                            dest_ratio = width / height
                            if im_ratio != dest_ratio:
                                if im_ratio > dest_ratio:
                                    height = round(frame.height / frame.width * width)
                                else:
                                    width = round(frame.width / frame.height * height)
                        self._current_img = frame.to_image(width=width, height=height, interpolation="FAST_BILINEAR")
                        self._frame_number += 1
                        self.event_generate("<<FrameGenerated>>")
                        if self._frame_number % self._video_info["framerate"] == 0:
                            self.event_generate("<<SecondChanged>>")
                        if self.consistant_frame_rate:
                            time.sleep(max((time_per_frame - delta) / 1000, 0))
                    except (StopIteration, av.error.EOFError, tk.TclError):
                        break
                self._container.close()
        finally:
            self._cleanup()
            gc.collect()

    def _cleanup(self):
        self._frame_number = 0
        self._paused = True
        self._stop = True
        self._load_thread = None
        if self._container:
            self._container.close()
            self._container = None
        try:
            self.event_generate("<<Ended>>")
        except tk.TclError:
            pass

    def load(self, path: str):
        self.stop()
        self.path = path

    def stop(self, event=None):
        self._paused = True
        self._stop = True
        self._cleanup()

    def pause(self):
        self._paused = True

    def play(self):
        self._paused = False
        self._stop = False
        if not self._load_thread:
            self._load_thread = threading.Thread(target=self._load, args=(self.path,), daemon=True)
            self._load_thread.start()

    def is_paused(self):
        return self._paused

    def video_info(self) -> Dict:
        return self._video_info

    def metadata(self) -> Dict:
        if self._container:
            return self._container.metadata
        return {}

    def current_frame_number(self) -> int:
        return self._frame_number

    def current_duration(self) -> float:
        return self._time_stamp

    def current_img(self) -> Image:
        return self._current_img

    def _display_frame(self, event):
        if hasattr(self, 'current_imgtk'):
            if self.current_imgtk.width() == self._current_img.width and self.current_imgtk.height() == self._current_img.height:
                self.current_imgtk.paste(self._current_img)
            else:
                self.current_imgtk = ImageTk.PhotoImage(self._current_img)
            self.config(image=self.current_imgtk)

    def seek(self, sec: float):
        self._seek = True
        self._seek_sec = sec


if __name__ == "__main__":
    def loop(e):
        tkvideo.play()

    root = tk.Tk()
    tkvideo = TkinterVideo(scaled=True, master=root)
    from src.config import DATA_DIR
    tkvideo.load(str(DATA_DIR / "videos" / "athlete_1.mp4"))
    tkvideo.pack(expand=True, fill="both")
    tkvideo.play()
    tkvideo.bind("<<Ended>>", loop)
    root.mainloop()
