import os
import re
import tkinter as tk
from tkinter import Listbox, messagebox, simpledialog

import cv2

from camera_recorder import CameraRecorder

RECORD_FOLDER = "record"


class VideoRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PM (# _ #)")
        self.root.geometry("480x320")
        self.camera_recorder = None
        self.selected_camera = None
        self.name = None
        self.is_streaming = False
        self.video_path = None
        self.window_name = "Video"

        # Nút menu chính
        self.load_button = tk.Button(root, text="Chạy Video", command=self.load_video)
        self.load_button.pack(pady=10)

        self.record_button = tk.Button(root, text="Ghi Video", command=self.record_video)
        self.record_button.pack(pady=10)

        # Danh sách video
        self.video_listbox = Listbox(root, width=40, height=5)
        self.video_listbox.pack(pady=10)

        # Khung chứa các nút Play, Delete, và Stream
        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        self.play_button = tk.Button(button_frame, text="Phát", command=self.play_selected_video)
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.stream_button = tk.Button(button_frame, text="Stream", command=self.stream_video)
        self.stream_button.pack(side=tk.LEFT, padx=5)

        self.delete_button = tk.Button(button_frame, text="Xóa", command=self.delete_selected_video)
        self.delete_button.pack(side=tk.LEFT, padx=5)

        # Sự kiện nhấp đúp để phát video
        self.video_listbox.bind('<Double-1>', self.play_selected_video)

    def load_video(self):
        self.video_listbox.delete(0, tk.END)  # Xóa danh sách video
        files = [f for f in os.listdir(RECORD_FOLDER) if f.endswith(".avi")]
        if not files:
            messagebox.showinfo("Không có video", "Không tìm thấy video nào.")
            return
        for file in files:
            self.video_listbox.insert(tk.END, file)

    def play_selected_video(self, event=None):
        try:
            selected_video = self.video_listbox.get(self.video_listbox.curselection())
            self.video_path = os.path.join(RECORD_FOLDER, selected_video)
            self.play_video(small_window=True)
        except tk.TclError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một video trước.")

    def delete_selected_video(self):
        try:
            selected_video = self.video_listbox.get(self.video_listbox.curselection())
            video_path = os.path.join(RECORD_FOLDER, selected_video)
            if messagebox.askyesno("Xóa", f"Bạn có chắc chắn muốn xóa '{selected_video}'?"):
                os.remove(video_path)
                self.load_video()  # Tải lại danh sách sau khi xóa
        except tk.TclError:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một video trước.")

    def play_video(self, small_window=True):
        # Lấy FPS từ tên file
        filename = os.path.basename(self.video_path)
        match = re.search(r'(\d+)@(\d+)', filename)
        if match:
            fps_str = f"{match.group(1)}.{match.group(2)}"
            fps = float(fps_str)
        else:
            # Mặc định FPS từ video file nếu không tìm thấy
            cap = cv2.VideoCapture(self.video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()

        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            messagebox.showerror("Lỗi", f"Không thể mở file video: {self.video_path}")
            return

        wait_time = int(1000 / fps)  # Chuyển FPS thành milliseconds

        # Tạo cửa sổ cho video
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        if small_window:
            cv2.resizeWindow(self.window_name, 480, 320)  # Kích thước cửa sổ nhỏ
        else:
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            cv2.setMouseCallback(self.window_name, lambda *args: None)  # Ẩn con trỏ chuột

        while True:  # Lặp để phát lại video
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    if small_window:
                        break  # Thoát nếu không lặp lại (chế độ cửa sổ nhỏ)
                    else:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Quay lại từ đầu khi hết video
                        continue  # Tiếp tục lặp lại

                cv2.imshow(self.window_name, frame)

                if cv2.waitKey(wait_time) & 0xFF == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return  # Thoát nếu nhấn 'q'

                if self.is_streaming:
                    cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

            if small_window:
                break  # Thoát khỏi vòng lặp nếu không lặp lại video (chế độ cửa sổ nhỏ)

            # Đặt lại video để tiếp tục lặp lại từ đầu
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        cap.release()
        cv2.destroyAllWindows()


    def stream_video(self):
        self.is_streaming = True
        # Ẩn con trỏ chuột
        # cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
        # cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        # cv2.setMouseCallback(self.window_name, lambda *args: None)  # Ẩn con trỏ chuột
        # Dừng cửa sổ nhỏ và chuyển sang toàn màn hình
        self.play_video(small_window=False)

    def record_video(self):
        self.name = simpledialog.askstring("Nhập tên", "Nhập tên (Không khoảng trắng, không ký tự đặc biệt):")
        if not self.name or not self.name.isalnum():
            messagebox.showerror("Không hợp lệ", "Tên không hợp lệ.")
            return

        self.selected_camera = self.select_camera()
        if self.selected_camera is not None:
            camera_index, camera_info = self.selected_camera
            filename = f'hocvien_{self.name}.avi'
            file_path = os.path.join(RECORD_FOLDER, filename)
            self.camera_recorder = CameraRecorder(camera_index=camera_index, camera_info=camera_info, output_path=file_path, parent=self.root)
            self.camera_recorder.run()

    def select_camera(self):
        cameras = self.check_cameras()
        if not cameras:
            messagebox.showerror("Không có", "Không tìm thấy camera.")
            return None

        camera_selection_window = tk.Toplevel(self.root)
        camera_selection_window.title("Chọn Camera")
        camera_selection_window.geometry("480x320")

        tk.Label(camera_selection_window, text="Camera khả dụng:").pack(pady=10)

        camera_listbox = tk.Listbox(camera_selection_window, width=40, height=5)
        for i, (_, info) in enumerate(cameras):
            camera_listbox.insert(tk.END, f"{i + 1}. {info}")
        camera_listbox.pack(pady=10)

        selected_camera = [None]  # Sử dụng list để lưu trữ kết quả

        def on_select():
            try:
                selection = camera_listbox.curselection()
                if selection:
                    selected_index = selection[0]
                    selected_camera[0] = cameras[selected_index]
                    camera_selection_window.destroy()
                else:
                    messagebox.showwarning("Lỗi lựa chọn", "Vui lòng chọn một camera từ danh sách.")
            except IndexError:
                messagebox.showerror("Lỗi lựa chọn", "Lựa chọn camera không hợp lệ.")
                camera_selection_window.destroy()

        tk.Button(camera_selection_window, text="Chọn", command=on_select).pack(pady=5)

        camera_selection_window.transient(self.root)
        camera_selection_window.grab_set()
        self.root.wait_window(camera_selection_window)

        return selected_camera[0]

    def check_cameras(self):
        available_cameras = []
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                info = f"Camera {i} ({width}x{height} @ {fps}fps)"
                available_cameras.append((i, info))
            cap.release()
        return available_cameras


def main():
    if not os.path.exists(RECORD_FOLDER):
        os.makedirs(RECORD_FOLDER)

    root = tk.Tk()
    app = VideoRecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
