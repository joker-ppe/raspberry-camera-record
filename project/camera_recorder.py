import os
import time
import cv2
import numpy as np

try:
    import mediapipe as mp

    print(f"MediaPipe version: {mp.__version__}")
except ImportError:
    print("MediaPipe not found. Please install mediapipe-rpi3.")
    mp = None


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

        # Tối ưu hóa độ phân giải cho Raspberry Pi 3B+
        self.width = 640  # Giảm từ 640
        self.height = 480  # Giảm từ 480
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.res = (self.width, self.height)

        self.fps = round(self.measure_fps(), 2)
        self.frame_duration = 1.0 / self.fps

        # Khởi tạo Face Detection với các tham số tối ưu
        if mp and hasattr(mp.solutions.face_detection, 'FaceDetection'):
            self.face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=0,  # 0 for short-range detection
                min_detection_confidence=0.5
            )
        else:
            self.face_detection = None
            print("Face detection is not available.")

        print(f"Camera FPS: {self.fps:.2f}, Resolution: {self.width}x{self.height}")

    def measure_fps(self, num_frames=50):  # Giảm số lượng frame để đo FPS
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
            actual_fps = 15  # Fallback FPS nếu không đo được

        print(f"Measured FPS: {actual_fps:.2f}")
        return min(actual_fps, 30)  # Giới hạn FPS tối đa là 30

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

    def detect_faces(self, frame):
        if self.face_detection and self.frame_count % 5 == 0:  # Phát hiện mỗi 5 frame
            results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if results.detections:
                for detection in results.detections:
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = frame.shape
                    bbox = int(bboxC.xmin * iw), int(bboxC.ymin * ih), \
                        int(bboxC.width * iw), int(bboxC.height * ih)
                    cv2.rectangle(frame, bbox, (255, 0, 0), 2)
        return frame

    def add_timer(self, frame):
        if self.is_recording:
            current_time = time.time() - self.start_time
            timer_text = f"Recording: {current_time:.2f}s"
            cv2.putText(frame, timer_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
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

        info_text = f"{self.camera_info} - FPS: {self.fps:.2f}"
        cv2.putText(button_frame, info_text, (width - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

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