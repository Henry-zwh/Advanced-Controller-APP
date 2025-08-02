import cv2
import queue
import threading
import time


class VideoRecorder:
    """A video recorder that captures frames from a camera and writes them to a video file."""
    """It uses a separate thread to write frames to ensure smooth recording without blocking the main thread."""

    def __init__(self, filename, resolution, target_fps):
        """Initialize the video recorder with a filename, resolution, and target FPS."""
        self.filename = filename
        self.width, self.height = resolution
        self.target_fps = target_fps
        self.frame_interval = 1.0 / self.target_fps
        # the buffer size is set to hold enough frames for 5 seconds
        self.frame_buffer = queue.Queue(maxsize=int(self.target_fps * 5))
        self.stop_event = threading.Event()
        self.recording_thread = None
        self.last_written_frame = None

    def put_frame(self, frame):
        """Producer: put a frame into the frame buffer."""
        timestamp = time.perf_counter() # get the timestamp of the frame
        try:
            self.frame_buffer.put_nowait((frame.copy(), timestamp))
        except queue.Full:
            print("warning: frame buffer is full, dropping frame")

    def _writer_thread(self):
        """Consumer: thread that writes frames to the video file."""
        fourcc = cv2.VideoWriter_fourcc(*'XVID') # set the codec
        video_writer = cv2.VideoWriter(self.filename, fourcc, self.target_fps, (self.width, self.height))
        # initialize the metronome
        next_frame_time = time.perf_counter()
        # main loop to write frames
        while not self.stop_event.is_set():
            try:
                current_frame, frame_timestamp = self.frame_buffer.get(timeout=0.1)
                self.last_written_frame = current_frame
                # write frames at the target FPS
                while next_frame_time < frame_timestamp:
                    video_writer.write(self.last_written_frame)
                    next_frame_time += self.frame_interval
                video_writer.write(current_frame)
                next_frame_time += self.frame_interval
            except queue.Empty:
                if self.stop_event.is_set():
                    break
                if self.last_written_frame is not None and time.perf_counter() > next_frame_time:
                     video_writer.write(self.last_written_frame) # copy the last frame if no new frame is available
                     next_frame_time += self.frame_interval
        # clear the remaining frames in the buffer
        while not self.frame_buffer.empty():
            frame, _ = self.frame_buffer.get_nowait()
            video_writer.write(frame)
        video_writer.release()
        print(f"The video is saved in {self.filename}")

    def start(self):
        """Start the recording thread."""
        if self.recording_thread is not None and self.recording_thread.is_alive():
            return
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self._writer_thread, daemon=True) # set as daemon to exit when the main thread exits
        self.recording_thread.start()

    def stop(self):
        """Stop the recording thread."""
        if self.recording_thread is None:
            return
        self.stop_event.set()
        self.recording_thread.join() # wait for the recording thread to finish
        self.recording_thread = None
