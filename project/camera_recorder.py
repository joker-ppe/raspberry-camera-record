import os
import time
import tkinter as tk

import cv2
from PIL import Image, ImageTk


class CameraRecorder:
    def __init__(self, camera_index=0, camera_info="Unknown Camera", output_path="output.mp4", width=480, height=320,
                 parent=None):
        self.camera_index = camera_index
        self.camera_info = camera_info
        self.cap = cv2.VideoCapture(self.camera_index)
        self.output_path = output_path
        self.is_recording = False
        self.output = None
        self.start_time = 0
        self.frame_count = 0

        self.width = width
        self.height = height
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.res = (self.width, self.height)

        # Initialize OpenCV Face Detection
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if self.face_cascade.empty():
                raise ValueError("Failed to load Haar Cascade classifier")
        except Exception as e:
            print(f"Error initializing OpenCV Face Detection: {e}")
            print("Face detection will be disabled.")
            self.face_cascade = None

        self.fps = round(self.measure_fps(), 2)
        self.frame_duration = 1.0 / self.fps

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

    def measure_fps(self, num_frames=100):
        print("Measuring FPS...")
        frame_times = []

        for _ in range(int(num_frames)):
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame during FPS measurement")
                break

            # Resize frame
            frame = cv2.resize(frame, (self.width, self.height))

            # Perform face detection (if available)
            self.detect_faces(frame)

            end_time = time.time()
            frame_time = end_time - start_time
            frame_times.append(frame_time)

        if len(frame_times) > 1:
            avg_frame_time = sum(frame_times) / len(frame_times)
            actual_fps = 1 / avg_frame_time
        else:
            actual_fps = 15  # Fallback FPS if measurement fails

        print(f"Measured FPS: {actual_fps:.2f}")
        return min(actual_fps, 30)  # Limit FPS to 30

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

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
            self.button.config(text="Stop Recording")
        else:
            self.stop_recording()
            self.button.config(text="Start Recording")

    def start_recording(self):
        if not self.is_recording:
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.output = cv2.VideoWriter(self.output_path + f"_{str(self.fps).replace('.', '@')}.mp4", fourcc,
                                          self.fps, self.res)

            if not self.output.isOpened():
                print("Error: Could not open video writer.")
                return

            self.is_recording = True
            self.start_time = time.time()
            self.frame_count = 0
            print(f"Recording started on {self.camera_info}...")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.output:
                self.output.release()
            duration = time.time() - self.start_time
            actual_fps = self.frame_count / duration
            print(f"Recording stopped on {self.camera_info}. Duration: {duration:.2f} seconds, "
                  f"Frames: {self.frame_count}, Actual FPS: {actual_fps:.2f}")

    def process_frame(self, frame):
        if self.is_recording and self.output and self.output.isOpened():
            self.output.write(frame)
            self.frame_count += 1

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
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (self.width, self.height))
            frame = self.detect_faces(frame)
            frame = self.add_timer(frame)
            self.process_frame(frame)

            # Convert the frame to RGB for displaying in Tkinter
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            photo = ImageTk.PhotoImage(image=Image.fromarray(rgb_frame))

            # Update the canvas with the new frame
            self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            self.canvas.image = photo

        self.window.after(int(self.frame_duration * 1000), self.update)

    def __del__(self):
        self.cap.release()
        if self.output:
            self.output.release()
