import os
import time

import cv2
import mediapipe as mp
import numpy as np


class CameraRecorder:
    def __init__(self, camera_index=0, camera_info="Unknown Camera", output_path="output.mp4"):
        self.camera_index = camera_index
        self.camera_info = camera_info
        self.cap = cv2.VideoCapture(self.camera_index)
        self.output_path = output_path
        self.is_recording = False
        self.output = None
        self.start_time = 0
        self.frame_count = 0
        self.window_name = f"Camera Recorder ({self.camera_info})"
        # self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.face_detection = mp.solutions.face_detection.FaceDetection()
        self.last_faces = []

        # Get resolution from camera
        # self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        # self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.width = 640
        self.height = 480
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.res = (self.width, self.height)

        # Get FPS from camera
        # self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        # self.fps = 15.0  # Set default FPS to 15
        # if self.fps <= 0 or self.fps > 60:  # If FPS is invalid, set default to 30
        #     self.fps = 30.0
        self.fps = round(self.measure_fps(), 2)
        self.frame_duration = 1.0 / self.fps

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
            end_time = time.time()
            frame_time = end_time - start_time
            frame_times.append(frame_time)

        if len(frame_times) > 1:
            avg_frame_time = sum(frame_times) / len(frame_times)
            actual_fps = 1 / avg_frame_time
        else:
            actual_fps = 0  # Fallback if we didn't measure any frames

        print(f"Measured FPS: {actual_fps:.2f}")
        return actual_fps

    def start_recording(self):
        if not self.is_recording:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

            # filename = f'output_camera_{self.camera_index}_{str(self.fps).replace('.','@')}.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # This codec works for MOV containers
            # self.output = cv2.VideoWriter(filename, fourcc, self.fps, self.res)
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
            # start_time = time.time()
            self.output.write(frame)
            self.frame_count += 1
            # process_time = time.time() - start_time
            # print(f"Frame {self.frame_count} written in {process_time:.4f} seconds")

    def detect_faces(self, frame):
        results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if results.detections:
            for detection in results.detections:
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                bbox = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                    int(bboxC.width * iw), int(bboxC.height * ih)
                cv2.rectangle(frame, bbox, (255, 0, 0), 2)
        return frame

    # def detect_faces(self, frame):
    #     # Chỉ phát hiện khuôn mặt trên mỗi 10 khung hình
    #     if self.frame_count % 10 == 0:
    #         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #         faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
    #         self.last_faces = faces  # Lưu kết quả phát hiện khuôn mặt
    #     else:
    #         faces = self.last_faces  # Sử dụng kết quả từ lần phát hiện trước
    #
    #     for (x, y, w, h) in faces:
    #         cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
    #     return frame

    def add_timer(self, frame):
        if self.is_recording:
            current_time = time.time() - self.start_time
            timer_text = f"Recording: {current_time:.2f}s"
            cv2.putText(frame, timer_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame

    def run(self):
        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.handle_click)

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print(f"Failed to grab frame from {self.camera_info}. Exiting...")
                break

            frame = self.detect_faces(frame)
            frame = self.add_timer(frame)
            self.process_frame(frame)

            frame_with_buttons = self.create_buttons(frame)
            cv2.imshow(self.window_name, frame_with_buttons)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                if self.is_recording:
                    self.stop_recording()
                break

        self.cap.release()
        if self.output:
            self.output.release()
        cv2.destroyAllWindows()

    def create_buttons(self, frame):
        height, width = frame.shape[:2]
        button_frame = np.zeros((50, width, 3), np.uint8)

        if not self.is_recording:
            cv2.rectangle(button_frame, (10, 10), (100, 40), (0, 255, 0), -1)
            cv2.putText(button_frame, "Start", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        else:
            cv2.rectangle(button_frame, (10, 10), (100, 40), (0, 0, 255), -1)
            cv2.putText(button_frame, "Stop", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Add camera info and FPS to the button frame
        info_text = f"{self.camera_info} - FPS: {self.fps:.2f}"
        cv2.putText(button_frame, info_text, (width - 400, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        frame_with_buttons = np.vstack((frame, button_frame))
        return frame_with_buttons

    def handle_click(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if height <= y <= height + 40 and 10 <= x <= 100:
                if not self.is_recording:
                    self.start_recording()
                else:
                    self.stop_recording()
