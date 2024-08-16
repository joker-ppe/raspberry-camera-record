import os
import platform
import tkinter as tk
from tkinter import filedialog, Listbox, messagebox, simpledialog

import cv2
import re

from camera_recorder import CameraRecorder

RECORD_FOLDER = "record"


class VideoRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Recorder App")
        self.camera_recorder = None
        self.selected_camera = None
        self.name = None

        # Main menu buttons
        self.load_button = tk.Button(root, text="Load Video", command=self.load_video)
        self.load_button.pack(pady=10)

        self.record_button = tk.Button(root, text="Record Video", command=self.record_video)
        self.record_button.pack(pady=10)

        # Listbox to show video files
        self.video_listbox = Listbox(root, width=50, height=10)
        self.video_listbox.pack(pady=10)
        self.video_listbox.bind('<Double-1>', self.play_selected_video)

    def load_video(self):
        self.video_listbox.delete(0, tk.END)  # Clear listbox
        files = [f for f in os.listdir(RECORD_FOLDER) if f.endswith(".mp4")]
        if not files:
            messagebox.showinfo("No Videos", "No video files found.")
            return
        for file in files:
            self.video_listbox.insert(tk.END, file)

    def play_selected_video(self, event):
        selected_video = self.video_listbox.get(self.video_listbox.curselection())
        video_path = os.path.join(RECORD_FOLDER, selected_video)
        self.play_video(video_path)

    def play_video(self, video_path):
        # Extract FPS from the filename
        filename = os.path.basename(video_path)
        match = re.search(r'(\d+)@(\d+)', filename)
        if match:
            fps_str = f"{match.group(1)}.{match.group(2)}"
            fps = float(fps_str)
        else:
            # Default to the FPS from the video file if no match is found
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            messagebox.showerror("Error", f"Failed to open video file: {video_path}")
            return

        wait_time = int(1000 / fps)  # Convert FPS to milliseconds

        while True:  # Loop indefinitely to replay video
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                cv2.imshow(f"Playing {filename}", frame)
                if cv2.waitKey(wait_time) & 0xFF == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return  # Exit both loops on 'q' key press

            # Restart the video by resetting the video capture position
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def record_video(self):
        self.name = tk.simpledialog.askstring("Input",
                                              "Enter the name for the recording (no spaces, no special characters):")
        if not self.name or not self.name.isalnum():
            messagebox.showerror("Invalid Name", "Invalid name. Only alphanumeric characters are allowed.")
            return

        self.selected_camera = self.select_camera()
        if self.selected_camera is not None:
            camera_index, camera_info = self.selected_camera
            filename = f'mem_{self.name}'
            file_path = os.path.join(RECORD_FOLDER, filename)
            self.camera_recorder = CameraRecorder(camera_index, camera_info, output_path=file_path)
            self.camera_recorder.run()

    def select_camera(self):
        cameras = self.check_cameras()
        if not cameras:
            messagebox.showerror("No Cameras", "No cameras found.")
            return None

        # Create a new window for camera selection
        camera_selection_window = tk.Toplevel(self.root)
        camera_selection_window.title("Select Camera")

        tk.Label(camera_selection_window, text="Available Cameras:").pack(pady=10)

        # Create a Listbox to show available cameras
        camera_listbox = tk.Listbox(camera_selection_window, width=50, height=10)
        for i, (_, info) in enumerate(cameras):
            camera_listbox.insert(tk.END, f"{i + 1}. {info}")
        camera_listbox.pack(pady=10)

        selected_camera = tk.StringVar()

        def on_select():
            try:
                selection = camera_listbox.curselection()
                if selection:
                    selected_index = int(selection[0])
                    selected_camera.set(selected_index)
                    camera_selection_window.destroy()
                else:
                    messagebox.showwarning("Selection Error", "Please select a camera from the list.")
            except IndexError:
                messagebox.showerror("Selection Error", "Invalid camera selection.")
                camera_selection_window.destroy()

        tk.Button(camera_selection_window, text="Select", command=on_select).pack(pady=5)

        camera_selection_window.transient(self.root)
        camera_selection_window.grab_set()
        self.root.wait_window(camera_selection_window)

        if selected_camera.get():
            return cameras[int(selected_camera.get())]
        else:
            return None

    def check_cameras(self):
        available_cameras = []
        for i in range(10):
            info = get_camera_info(i)
            if info:
                available_cameras.append((i, info))
        return available_cameras


def get_camera_info(index):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Attempt to get the camera name
    if platform.system() == "Darwin":  # macOS
        name = f"Camera {index}"  # macOS doesn't provide easy access to camera names
    elif platform.system() == "Linux":  # Raspberry Pi OS
        name = f"Camera {index}"  # Basic name for Linux systems
    else:  # Windows or other systems
        name = cap.getBackendName()

    cap.release()
    return f"{name} ({width}x{height} @ {fps}fps)"


def main():
    if not os.path.exists(RECORD_FOLDER):
        os.makedirs(RECORD_FOLDER)

    root = tk.Tk()
    app = VideoRecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
