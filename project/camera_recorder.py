import os
import time
import json
import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from queue import Queue
from threading import Thread
import subprocess

# Define constants for directories
TEMP_DIR = "tmp"
RECORD_DIR = "record"


class CameraRecorder:
    def __init__(self, camera_index=0, camera_info="USB Camera", output_path="output.mp4", width=320, height=240,
                 parent=None):
        self.camera_index = camera_index
        self.camera_info = camera_info
        self.output_path = output_path
        self.is_recording = False
        self.start_time = 0
        self.frame_count = 0
        self.actual_duration = 0

        self.width = width
        self.height = height

        # Ensure directories exist
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(RECORD_DIR, exist_ok=True)

        self.cap = self.init_camera()
        if not self.cap.isOpened():
            raise ValueError(f"Could not open camera with index {camera_index}")

        self.set_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.set_fps <= 0 or self.set_fps > 120:  # Sanity check
            self.set_fps = 30  # Default to 30 FPS if unable to get from camera
        self.frame_duration = 1.0 / self.set_fps
        self.actual_fps = 0
        self.frame_queue = Queue(maxsize=128)
        self.recording_thread = None

        # Tkinter window setup
        self.parent = parent
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Camera Recorder ({self.camera_info})")
        self.window.geometry(f"{self.width}x{self.height + 80}")

        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack()

        self.timer_label = tk.Label(self.window, text="", font=("Arial", 12))
        self.timer_label.pack(pady=5)

        self.record_button = tk.Button(self.window, text="Bắt đầu ghi hình", command=self.toggle_recording)
        self.record_button.pack(pady=5)

        print(f"Camera FPS: {self.set_fps:.2f}, Resolution: {self.width}x{self.height}")

    def init_camera(self):
        backends = [cv2.CAP_ANY, cv2.CAP_V4L, cv2.CAP_V4L2, cv2.CAP_GSTREAMER]
        for backend in backends:
            cap = cv2.VideoCapture(self.camera_index + backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                return cap
        return cv2.VideoCapture(self.camera_index)  # Fallback to default

    def start_recording(self):
        if not self.is_recording:
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                base_filename = f"{timestamp}_{os.path.basename(self.output_path)}"
                self.temp_video_path = os.path.join(TEMP_DIR, f"temp_{base_filename}")
                self.final_video_path = os.path.join(RECORD_DIR, base_filename)

                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                self.out = cv2.VideoWriter(self.temp_video_path, fourcc, self.set_fps, (self.width, self.height))

                if not self.out.isOpened():
                    raise Exception("Failed to open VideoWriter")

                self.is_recording = True
                self.start_time = time.time()
                self.frame_count = 0
                print(f"Recording started on {self.camera_info}...")
                print(f"Temporary file: {self.temp_video_path}")
                print(f"Final file will be: {self.final_video_path}")

                self.recording_thread = Thread(target=self.record_frames)
                self.recording_thread.start()

                self.record_button.config(text="Dừng ghi hình")

            except Exception as e:
                error_message = f"Failed to start recording: {str(e)}\n"
                error_message += f"Current working directory: {os.getcwd()}\n"
                error_message += f"Temp directory: {TEMP_DIR}, exists: {os.path.exists(TEMP_DIR)}\n"
                error_message += f"Record directory: {RECORD_DIR}, exists: {os.path.exists(RECORD_DIR)}\n"
                error_message += f"Temp file path: {self.temp_video_path}\n"
                error_message += f"Write permission (temp): {os.access(TEMP_DIR, os.W_OK)}\n"
                error_message += f"Write permission (record): {os.access(RECORD_DIR, os.W_OK)}\n"
                error_message += f"OpenCV version: {cv2.__version__}"
                messagebox.showerror("Error", error_message)
                print(error_message)

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join()
            if hasattr(self, 'out') and self.out.isOpened():
                self.out.release()
                self.actual_duration = time.time() - self.start_time
                self.actual_fps = self.frame_count / self.actual_duration

                print("Converting video...")
                self.convert_video()

                message = f"Ghi hình trên {self.camera_info}.\nThời gian: {self.actual_duration:.2f} giây\n" \
                          f"Frames: {self.frame_count}\nSet FPS: {self.set_fps:.2f}\nActual FPS: {self.actual_fps:.2f}\n" \
                          f"Lưu: {self.final_video_path}"
                print(message)
                messagebox.showinfo("Ghi hình hoàn thành", message)
            else:
                print("Error: VideoWriter was not properly initialized or opened.")

            self.record_button.config(text="Bắt đầu ghi hình")
            self.timer_label.config(text="")

    def get_video_info(self, video_path):
        command = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-count_packets',
            '-show_entries', 'stream=duration,r_frame_rate,nb_read_packets',
            '-of', 'json',
            video_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        info = json.loads(result.stdout)
        stream = info['streams'][0]

        duration = stream['duration']
        fps = eval(stream['r_frame_rate'])  # This is usually a string like '30000/1001'
        packet_count = stream['nb_read_packets']

        return {
            'duration': duration,
            'fps': fps,
            'packet_count': packet_count
        }

    def convert_video(self):
        cap = cv2.VideoCapture(self.temp_video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate the actual FPS based on the recorded duration
        actual_fps = total_frames / self.actual_duration

        print(f"Reported FPS: {cap.get(cv2.CAP_PROP_FPS)}")
        print(f"Calculated actual FPS: {actual_fps}")
        print(f"Total frames: {total_frames}")
        print(f"Actual duration: {self.actual_duration:.2f} seconds")

        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(self.final_video_path, fourcc, actual_fps, (self.width, self.height))

        frames_written = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            out.write(frame)
            frames_written += 1

            if frames_written % 100 == 0:
                print(f"Converting: {frames_written}/{total_frames} frames processed")

        cap.release()
        out.release()

        # Verify the duration of the converted video
        cap = cv2.VideoCapture(self.final_video_path)
        converted_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        converted_fps = cap.get(cv2.CAP_PROP_FPS)
        converted_duration = converted_frame_count / converted_fps
        cap.release()

        print("Conversion completed successfully!")
        print(f"Actual recorded duration: {self.actual_duration:.2f} seconds")
        print(f"Converted video duration: {converted_duration:.2f} seconds")
        print(f"Duration difference: {abs(self.actual_duration - converted_duration):.2f} seconds")
        print(f"Frames written: {frames_written}")
        print(f"Converted frame count: {converted_frame_count}")
        print(f"Converted FPS: {converted_fps}")

        os.remove(self.temp_video_path)  # Remove temporary file

    def record_frames(self):
        while self.is_recording:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                if self.out.isOpened():
                    self.out.write(frame)
                    self.frame_count += 1

    def update_timer(self):
        if self.is_recording:
            current_time = time.time() - self.start_time
            self.timer_label.config(text=f"Thời gian: {current_time:.2f}s")
        else:
            self.timer_label.config(text="")

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def run(self):
        self.update()
        self.window.mainloop()

    def update(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (self.width, self.height))

            if self.is_recording:
                self.frame_queue.put(frame)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=image)

            self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.canvas.image = photo

            self.update_timer()

        self.window.after(int(self.frame_duration * 1000), self.update)

    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
        if hasattr(self, 'out') and self.out.isOpened():
            self.out.release()