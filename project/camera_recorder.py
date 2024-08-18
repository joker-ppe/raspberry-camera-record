import os
import time
import tkinter as tk
import cv2
import numpy as np
import subprocess


class CameraRecorder:
    def __init__(self, camera_index=0, camera_info="Raspberry Pi Camera", output_path="output.h264", width=640,
                 height=480,
                 parent=None):
        self.camera_index = camera_index
        self.camera_info = camera_info
        self.output_path = output_path
        self.is_recording = False
        self.start_time = 0
        self.frame_count = 0

        self.width = width
        self.height = height
        self.res = f"{self.width}x{self.height}"

        self.fps = 30
        self.frame_duration = 1.0 / self.fps

        self.preview_process = None
        self.record_process = None

        # Initialize OpenCV Face Detection
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if self.face_cascade.empty():
                raise ValueError("Failed to load Haar Cascade classifier")
        except Exception as e:
            print(f"Error initializing OpenCV Face Detection: {e}")
            print("Face detection will be disabled.")
            self.face_cascade = None

        # Tkinter window setup
        self.parent = parent
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Camera Recorder ({self.camera_info})")
        self.window.geometry(f"{self.width}x{self.height + 50}")

        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack()

        self.button = tk.Button(self.window, text="Start Recording", command=self.toggle_recording)
        self.button.pack(pady=10)

        self.info_label = tk.Label(self.window, text=f"FPS: {self.fps:.2f}")
        self.info_label.pack()

        print(f"Camera FPS: {self.fps:.2f}, Resolution: {self.width}x{self.height}")

        # Start preview
        self.start_preview()

    def start_preview(self):
        preview_command = f"libcamera-vid -t 0 --width {self.width} --height {self.height} --framerate {self.fps} --inline --listen -o tcp://127.0.0.1:8888"
        self.preview_process = subprocess.Popen(preview_command, shell=True)
        time.sleep(2)  # Give some time for the preview to start

    def start_recording(self):
        if not self.is_recording:
            try:
                os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                full_path = self.output_path + f"_{self.fps}.h264"

                record_command = f"libcamera-vid -t 0 --width {self.width} --height {self.height} --framerate {self.fps} -o {full_path}"
                self.record_process = subprocess.Popen(record_command, shell=True)

                self.is_recording = True
                self.start_time = time.time()
                self.frame_count = 0
                print(f"Recording started on {self.camera_info}...")
                print(f"Saving video to: {full_path}")
            except Exception as e:
                print(f"Error: Could not start recording. Details: {str(e)}")
                print(f"Current working directory: {os.getcwd()}")
                print(f"Output path: {self.output_path}")
                print(
                    f"Permissions on output directory: {oct(os.stat(os.path.dirname(self.output_path)).st_mode)[-3:]}")
        else:
            print("Already recording.")

    def stop_recording(self):
        if self.is_recording:
            self.record_process.terminate()
            self.is_recording = False
            duration = time.time() - self.start_time
            actual_fps = self.frame_count / duration
            print(f"Recording stopped on {self.camera_info}. Duration: {duration:.2f} seconds, "
                  f"Frames: {self.frame_count}, Actual FPS: {actual_fps:.2f}")

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
            self.button.config(text="Stop Recording")
        else:
            self.stop_recording()
            self.button.config(text="Start Recording")

    def detect_faces(self, frame):
        if self.face_cascade is None:
            return frame

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        except Exception as e:
            print(f"Error during face detection: {e}")

        return frame

    def add_timer(self, frame):
        if self.is_recording:
            current_time = time.time() - self.start_time
            timer_text = f"Recording: {current_time:.2f}s"
            cv2.putText(frame, timer_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        return frame

    def run(self):
        self.update()
        self.window.mainloop()

    def update(self):
        cap = cv2.VideoCapture("tcp://127.0.0.1:8888")
        while True:
            ret, frame = cap.read()
            if ret:
                frame = self.detect_faces(frame)
                frame = self.add_timer(frame)

                if self.is_recording:
                    self.frame_count += 1

                # Convert the frame to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Convert to PhotoImage
                photo = tk.PhotoImage(data=cv2.imencode('.png', rgb_frame)[1].tobytes())

                # Update the canvas with the new frame
                self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                self.canvas.image = photo

                self.window.update()

                if not self.window.winfo_exists():
                    break
            else:
                break

        cap.release()

    def __del__(self):
        if hasattr(self, 'preview_process') and self.preview_process:
            self.preview_process.terminate()
        if hasattr(self, 'record_process') and self.record_process:
            self.record_process.terminate()