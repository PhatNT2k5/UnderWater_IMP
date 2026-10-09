"""Tkinter mission dashboard; all simulation work runs in an isolated process."""
from __future__ import annotations

from collections import deque
from datetime import datetime
import json
import multiprocessing as mp
import os
from pathlib import Path
from queue import Empty
import sys
import time
import tkinter as tk
from tkinter import ttk

from PIL import ImageGrab
import win32api

from auv_inspection.patchcore_data.approval_gate import approval_matches
from .bridge import INSPECTION, ROOT, run_worker
from .viewport import UnrealViewport
from .widgets import COLORS, FONT, CameraTile, RouteMap

sys.path.insert(0, str(INSPECTION))
from inspection_route import ROUTE

PATCHCORE_MODEL = ROOT / "auv_inspection/output/patchcore_model_v1"
PATCHCORE_REFERENCE = ROOT / "auv_inspection/output/patchcore_dataset_clean_20260925"
PATCHCORE_THRESHOLDS = ROOT / "auv_inspection/output/patchcore_thresholds_v1.json"
PATCHCORE_EVALUATION = ROOT / "auv_inspection/output/patchcore_evaluation_B_v1.json"


def default_detector() -> str:
    return ("PatchCore" if approval_matches(
        PATCHCORE_MODEL, PATCHCORE_REFERENCE,
        PATCHCORE_THRESHOLDS, PATCHCORE_EVALUATION,
    ) else "Classical")


class Dashboard:
    def __init__(self, root: tk.Tk, steps: int = 60000, smoke_test: bool = False) -> None:
        self.root, self.steps, self.smoke_test = root, steps, smoke_test
        self.context = mp.get_context("spawn")
        self.worker: mp.Process | None = None
        self.engine_pid: int | None = None
        self.session: Path | None = None
        self.runtime_output: Path | None = None
        self.commands = self.frames = self.events = None
        self.paused = False
        self.damage_paused = False
        self.closing = False
        self.stopping = False
        self.finished = False
        self.worker_handled = False
        self.stop_at = 0.0
        self.keys: set[int] = set()
        self.packet: dict[str, object] | None = None
        self.arrivals: deque[float] = deque(maxlen=30)
        self.alerts: list[dict] = []
        self.qa: dict[str, object] = {"ticks": [], "embedded": False, "continued": False}
        self.qa_pause_done = False
        self.qa_resume_at: float | None = None
        self.qa_continue_at: float | None = None
        self.qa_started = time.monotonic()
        self._configure()
        self._build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        root.bind("<FocusOut>", lambda _event: self.release_keys())
        root.after(33, self.poll)

    def _configure(self) -> None:
        self.root.title("AUV Observatory | Khảo sát công trình ngầm")
        width = min(1440, self.root.winfo_screenwidth() - 60)
        height = min(920, self.root.winfo_screenheight() - 90)
        self.root.geometry(f"{width}x{height}+24+24")
        self.root.minsize(1080, 700)
        self.root.configure(bg=COLORS["bg"])
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", font=(FONT, 10), padding=5)
        style.configure("Horizontal.TProgressbar", background=COLORS["sea"], troughcolor="#dce8ec", borderwidth=0)

    def label(self, parent: tk.Misc, text: str, size: int = 10, color: str | None = None,
              bold: bool = False, **kwargs: object) -> tk.Label:
        return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                        fg=color or COLORS["ink"], bg=parent.cget("bg"), **kwargs)

    def button(self, parent: tk.Misc, text: str, command: object, primary: bool = False) -> tk.Button:
        return tk.Button(parent, text=text, command=command, font=(FONT, 10, "bold"),
                         bg=COLORS["sea"] if primary else "#e6eff2", fg="white" if primary else COLORS["ink"],
                         activebackground="#0b6c78" if primary else "#d1e4e9",
                         activeforeground="white" if primary else COLORS["ink"],
                         relief="flat", bd=0, padx=15, pady=9, cursor="hand2", takefocus=True)

    def _build(self) -> None:
        header = tk.Frame(self.root, bg=COLORS["navy"], height=72)
        header.pack(fill="x")
        brand = tk.Frame(header, bg=COLORS["navy"])
        brand.pack(side="left", padx=24, pady=14)
        self.label(brand, "AUV Observatory", 21, "#ffffff", True).pack(anchor="w")
        self.label(brand, "Khảo sát đường ống & công trình ngầm", 10, "#a8c7d6").pack(anchor="w")
        self.status = self.label(header, "●  Sẵn sàng", 11, "#9ee5df")
        self.status.pack(side="right", padx=24)

        controls = tk.Frame(self.root, bg=COLORS["panel"])
        controls.pack(fill="x", padx=18, pady=(12, 10))
        self.mode = tk.StringVar(value="Tự động")
        self.mode_box = ttk.Combobox(controls, textvariable=self.mode, values=["Tự động", "Thủ công"], state="readonly", width=12)
        self.mode_box.pack(side="left", padx=10)
        self.detector = tk.StringVar(value="Classical" if self.smoke_test else default_detector())
        self.detector_box = ttk.Combobox(controls, textvariable=self.detector,
                                         values=["Classical", "PatchCore"], state="readonly", width=12)
        self.detector_box.pack(side="left", padx=(0, 10))
        self.start_button = self.button(controls, "Bắt đầu khảo sát", self.start, True)
        self.start_button.pack(side="left", padx=(0, 8), pady=8)
        self.pause_button = self.button(controls, "Tạm dừng", self.toggle_pause)
        self.pause_button.pack(side="left", padx=(0, 8))
        self.continue_button = self.button(controls, "Tiếp tục sau cảnh báo", self.continue_run)
        self.continue_button.pack(side="left", padx=(0, 8))
        self.stop_button = self.button(controls, "Dừng", self.stop)
        self.stop_button.pack(side="left")
        self.button(controls, "Mở kết quả", self.open_output).pack(side="right", padx=10)
        for button in (self.pause_button, self.continue_button, self.stop_button):
            button.configure(state="disabled")

        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=18)
        body.grid_columnconfigure(0, minsize=254)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=3, minsize=290)
        body.grid_rowconfigure(1, weight=2, minsize=225)

        sidebar = tk.Frame(body, bg=COLORS["panel"], width=254)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12), pady=(0, 12))
        sidebar.grid_propagate(False)
        route_head = tk.Frame(sidebar, bg=COLORS["panel"])
        route_head.pack(fill="x", padx=16, pady=(12, 0))
        self.label(route_head, "Lộ trình khảo sát 3D", 13, bold=True).pack(side="left")
        self.route_map = RouteMap(sidebar, ROUTE, width=400, height=400)
        tk.Button(route_head, text="↻", command=self.route_map.reset_view, bg="#f3f8fa",
                  fg=COLORS["sea"], activebackground="#deedf0", relief="flat", bd=0,
                  font=(FONT, 11), width=2, cursor="hand2").pack(side="right")
        self.label(sidebar, "Kéo để xoay · cuộn để thu phóng", 9, COLORS["muted"]).pack(anchor="w", padx=16)
        self.route_map.pack(fill="x", padx=2, pady=6)
        self.label(sidebar, "┄ Kế hoạch   ━ Đã đi   ◆ Hư hại   ▲ AUV", 8, COLORS["sea"]).pack(anchor="w", padx=13)
        self.progress = ttk.Progressbar(sidebar, maximum=100, mode="determinate")
        self.progress.pack(fill="x", padx=16, pady=(14, 4))
        self.progress_label = self.label(sidebar, "0 / 359 điểm tuyến", 9, COLORS["muted"])
        self.progress_label.pack(anchor="w", padx=16)
        self.depth = self.label(sidebar, "— m", 26, bold=True)
        self.depth.pack(anchor="w", padx=16, pady=(10, 0))
        self.label(sidebar, "Độ sâu hiện tại", 9, COLORS["muted"]).pack(anchor="w", padx=17)
        self.telemetry = self.label(sidebar, "Vận tốc  — m/s\nHướng  —°\nVị trí  —", 10, justify="left", anchor="w")
        self.telemetry.pack(fill="x", padx=16, pady=8)
        self.label(sidebar, "Phát hiện hư hại", 12, bold=True).pack(anchor="w", padx=16, pady=(8, 6))
        self.alert_list = tk.Listbox(sidebar, height=4, bg="#f3f8fa", fg=COLORS["ink"], font=(FONT, 9),
                                    bd=0, highlightthickness=0, activestyle="none", selectbackground="#cde8ea")
        self.alert_list.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.alert_list.bind("<Double-1>", self.open_alert)
        self.label(sidebar, "Nhấp đúp cảnh báo để xem ảnh", 8, COLORS["muted"]).pack(anchor="w", padx=13, pady=(0, 10))

        scene = tk.Frame(body, bg=COLORS["panel"])
        scene.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        scene_head = tk.Frame(scene, bg=COLORS["panel"])
        scene_head.pack(fill="x")
        self.label(scene_head, "Góc nhìn thứ ba", 13, bold=True).pack(side="left", padx=14, pady=9)
        self.follow = tk.BooleanVar(value=True)
        tk.Checkbutton(scene_head, text="Theo AUV", variable=self.follow, command=self.set_follow,
                       bg="white", fg=COLORS["muted"], font=(FONT, 9), activebackground="white").pack(side="right", padx=12)
        self.scene_area = tk.Frame(scene, bg=COLORS["navy"])
        self.scene_area.pack(fill="both", expand=True)
        self.host = tk.Frame(self.scene_area, bg=COLORS["navy"])
        self.host.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.placeholder = self.label(self.host, "Bắt đầu khảo sát để mở góc nhìn Unreal", 12, "#a9c4d0")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self.viewport = UnrealViewport(self.host)
        self.host.bind("<Configure>", lambda _event: self.viewport.resize())
        self.pip = tk.Frame(self.scene_area, bg="white", padx=2, pady=2)
        self.pip.place(relx=1, x=-12, y=12, anchor="ne", width=282, height=230)
        self.label(self.pip, "Camera robot", 9, bold=True).pack(anchor="w", padx=6, pady=(1, 3))
        self.robot_camera = CameraTile(self.pip, "Chờ InspectionCamera")
        self.robot_camera.pack(fill="both", expand=True)

        pipeline = tk.Frame(body, bg=COLORS["bg"])
        pipeline.grid(row=1, column=1, sticky="nsew", pady=(0, 12))
        head = tk.Frame(pipeline, bg=COLORS["bg"])
        head.pack(fill="x", pady=(0, 8))
        self.label(head, "Các bước xử lý ảnh", 14, bold=True).pack(side="left")
        self.detector_status = self.label(head, "Chờ dữ liệu cảm biến", 9, COLORS["muted"])
        self.detector_status.pack(side="right")
        tiles = tk.Frame(pipeline, bg=COLORS["bg"])
        tiles.pack(fill="both", expand=True)
        self.tiles: list[CameraTile] = []
        titles = [("01  Tăng tương phản", "Grayscale + CLAHE"),
                  ("02  Vùng nghi vấn", "Mask từ bộ phát hiện"),
                  ("03  Kết quả", "Vùng qua bộ lọc hình học")]
        self.stage_titles: list[tk.Label] = []
        self.stage_captions: list[tk.Label] = []
        for index, (title, caption) in enumerate(titles):
            tiles.grid_columnconfigure(index, weight=1, uniform="stage")
            panel = tk.Frame(tiles, bg=COLORS["panel"])
            panel.grid(row=0, column=index, sticky="nsew",
                       padx=(0 if index == 0 else 5, 0 if index == len(titles) - 1 else 5))
            heading = self.label(panel, title, 10, bold=True)
            heading.pack(anchor="w", padx=9, pady=6)
            self.stage_titles.append(heading)
            tile = CameraTile(panel)
            tile.pack(fill="both", expand=True)
            self.tiles.append(tile)
            subtitle = self.label(panel, caption, 8, COLORS["muted"])
            subtitle.pack(anchor="w", padx=9, pady=5)
            self.stage_captions.append(subtitle)
        tiles.grid_rowconfigure(0, weight=1)

        footer = tk.Frame(self.root, bg=COLORS["navy"])
        footer.pack(fill="x")
        self.station_label = self.label(footer, "Chưa bắt đầu · Dữ liệu trực tiếp từ mô phỏng", 9, "#bdd1dd")
        self.station_label.pack(side="left", padx=18, pady=8)
        self.fps_label = self.label(footer, "Cảnh báo: tự tiếp tục sau 5 giây  |  Esc: dừng", 9, "#bdd1dd")
        self.fps_label.pack(side="right", padx=18)

    def send(self, name: str, **payload: object) -> None:
        if self.commands is not None and self.worker and self.worker.is_alive():
            self.commands.put({"type": name, **payload})

    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        selected_detector = self.detector.get()
        if selected_detector == "PatchCore":
            if self.mode.get() != "Tự động":
                self.status.configure(text="●  PatchCore hiện chỉ dùng tuyến tự động", fg="#ffb79b")
                return
            if not PATCHCORE_THRESHOLDS.is_file():
                self.status.configure(text="●  PatchCore chưa có ngưỡng hiệu chỉnh", fg="#ffb79b")
                return
        stage_text = (["01  Bề mặt phân tích", "02  Bản đồ bất thường", "03  Kết quả"]
                      if selected_detector == "PatchCore" else
                      ["01  Tăng tương phản", "02  Vùng nghi vấn", "03  Kết quả"])
        caption_text = (["ROI từ ảnh sạch đã duyệt", "Điểm bất thường, chưa phải xác suất",
                         "Vùng nghi vấn đã xác nhận"]
                        if selected_detector == "PatchCore" else
                        ["Grayscale + CLAHE", "Mask từ bộ phát hiện",
                         "Vùng qua bộ lọc hình học"])
        for label, value in zip(self.stage_titles, stage_text):
            label.configure(text=value)
        for label, value in zip(self.stage_captions, caption_text):
            label.configure(text=value)
        for channel in (self.commands, self.frames, self.events):
            if channel is not None:
                channel.close()
        self.session = ROOT / "auv_dashboard/output" / datetime.now().strftime("session_%Y%m%d_%H%M%S_%f")
        self.session.mkdir(parents=True)
        self.commands, self.frames, self.events = self.context.Queue(), self.context.Queue(maxsize=2), self.context.Queue()
        self.alerts.clear()
        self.alert_list.delete(0, "end")
        self.route_map.clear_run()
        self.arrivals.clear()
        for tile in [*self.tiles, self.robot_camera]:
            tile.clear()
        self.qa = {"ticks": [], "embedded": False, "continued": False}
        self.qa["detector"] = selected_detector
        self.qa_pause_done = False
        self.qa_resume_at = self.qa_continue_at = None
        self.qa_started = time.monotonic()
        self.keys.clear()
        self.packet = None
        self.engine_pid = None
        self.runtime_output = None
        self.paused = self.damage_paused = self.stopping = False
        self.finished = self.worker_handled = False
        self.pause_button.configure(text="Tạm dừng", state="disabled")
        self.continue_button.configure(state="disabled")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self.placeholder.configure(text="Đang mở góc nhìn Unreal…")
        self.mode_box.configure(state="disabled")
        self.detector_box.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status.configure(text="●  Đang khởi động…", fg="#f3cf91")
        self.worker = self.context.Process(target=run_worker, args=(self.commands, self.frames, self.events, {
            "session": str(self.session), "steps": self.steps,
            "follow": self.follow.get(),
            "mode": "auto" if self.mode.get() == "Tự động" else "manual",
            "detector": selected_detector,
            "patchcore_model": str(PATCHCORE_MODEL),
            "patchcore_reference": str(PATCHCORE_REFERENCE),
            "patchcore_thresholds": str(PATCHCORE_THRESHOLDS),
        }), name="AUV-dashboard-worker")
        self.worker.start()

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.send("pause", value=self.paused)
        self.pause_button.configure(text="Chạy tiếp" if self.paused else "Tạm dừng")
        self.status.configure(text="●  Tạm dừng" if self.paused else "●  Đang khảo sát", fg="#f3cf91" if self.paused else "#9ee5df")

    def continue_run(self) -> None:
        self.send("continue")
        self.damage_paused = self.paused = False
        self.pause_button.configure(text="Tạm dừng", state="normal")
        self.continue_button.configure(state="disabled")
        self.status.configure(text="●  Đang khảo sát", fg="#9ee5df")

    def set_follow(self) -> None:
        self.send("follow", value=self.follow.get())

    def stop(self) -> None:
        if self.worker and self.worker.is_alive():
            self.stopping = True
            self.stop_at = time.monotonic()
            self.send("stop")
            self.status.configure(text="●  Đang dừng mô phỏng…", fg="#f3cf91")
            self.stop_button.configure(state="disabled")

    def key_down(self, event: tk.Event) -> None:
        if event.keysym == "space":
            self.continue_run()
        elif event.keysym == "Escape":
            self.stop()
        elif event.char.upper() in "WSADRFQE" and event.char:
            self.keys.add(ord(event.char.upper()))
            self.send("keys", value=list(self.keys))

    def key_up(self, event: tk.Event) -> None:
        if len(event.char) == 1:
            self.keys.discard(ord(event.char.upper()))
            self.send("keys", value=list(self.keys))

    def release_keys(self) -> None:
        if self.keys:
            self.keys.clear()
            self.send("keys", value=[])

    def open_output(self) -> None:
        if self.runtime_output and self.runtime_output.exists():
            os.startfile(str(self.runtime_output))

    def open_alert(self, _event: tk.Event) -> None:
        selected = self.alert_list.curselection()
        if selected:
            os.startfile(str(Path(self.alerts[selected[0]]["event_dir"]) / "annotated.png"))

    def handle_event(self, event: dict) -> None:
        kind = event["type"]
        if kind == "engine":
            self.engine_pid = event["pid"]
            self.runtime_output = Path(event["output"])
        elif kind == "damage":
            self.damage_paused = True
            self.alerts.append(event["event"])
            item = event["event"]
            self.route_map.add_alert(item["position_m"])
            self.alert_list.insert("end", f"{len(self.alerts):02d}  Nghi vấn · x={item['position_m'][0]:.1f} m")
            self.continue_button.configure(state="normal")
            self.status.configure(text="●  Phát hiện hư hại · Giữ vị trí 5 giây rồi tự tiếp tục", fg="#ffd08a")
            if self.smoke_test and self.qa_continue_at is None:
                self.qa_continue_at = time.monotonic() + 1.0
        elif kind == "damage_resumed":
            self.damage_paused = False
            self.continue_button.configure(state="disabled")
        elif kind == "status":
            self.status.configure(text="●  " + event["text"])
        elif kind == "error":
            self.finished = True
            self.status.configure(text="●  Có lỗi · xem worker.log", fg="#ffb79b")
            self.qa["error"] = event["text"]
            self.station_label.configure(text=event["text"].strip().splitlines()[-1][:150])
        elif kind == "finished":
            self.finished = True
            self.qa["report"] = event["report"]
            self.status.configure(text="●  Hoàn tất" if event["report"].get("route_completed") else "●  Đã dừng", fg="#bdd1dd")

    def render_packet(self, packet: dict) -> None:
        self.packet = packet
        self.arrivals.append(time.monotonic())
        for tile, data in zip(self.tiles, packet["frames"][1:]):
            tile.set_frame(data)
        self.robot_camera.set_frame(packet["camera"])
        position = packet["position"]
        self.route_map.update_position(position, packet["yaw"])
        self.depth.configure(text=f"{abs(position[2]):.2f} m")
        self.telemetry.configure(text=f"Vận tốc   {packet['speed']:.2f} m/s\nHướng      {packet['yaw']:.0f}°\nX {position[0]:.1f}   Y {position[1]:.1f}")
        index, count = packet["station_index"], packet["total_stations"]
        self.progress.configure(value=100 * index / max(1, count - 1))
        self.progress_label.configure(text=f"{index + 1} / {count} điểm tuyến")
        active = packet["detector_active"]
        damage_pause = bool(packet["damage_pause"])
        if damage_pause:
            remaining = float(packet.get("damage_pause_remaining_seconds", 0.0))
            self.damage_paused = True
            self.continue_button.configure(state="normal")
            self.status.configure(
                text=f"●  Phát hiện hư hại · Tự tiếp tục sau {remaining:.1f} giây",
                fg="#ffd08a",
            )
        if packet["evidence_tick"] is not None:
            text = f"Ảnh cảnh báo · tick {packet['evidence_tick']} · Camera robot vẫn trực tiếp"
        elif active and packet.get("analysis_reason") == "diffuse_anomaly":
            # Widespread anomaly: environment change or large-area damage, never "clean".
            text = "Bất thường lan rộng trên bề mặt · cần kiểm tra thủ công"
        elif active and packet.get("analysis_status") == "analysis_unavailable":
            text = "Chưa đủ điều kiện phân tích · thiếu ROI/căn chỉnh"
        elif packet.get("detector") == "PatchCore" and active:
            analysis_tick = packet.get("analysis_tick")
            text = (f"PatchCore · {packet['candidate_count']} vùng nghi vấn · "
                    f"ảnh phân tích tick {analysis_tick}" if analysis_tick is not None
                    else "PatchCore · đang chờ frame phân tích")
        else:
            text = f"Đang phân tích · {packet['candidate_count']} vùng nghi vấn" if active else "Ngoài đoạn quét · mask trống"
        self.detector_status.configure(text=text, fg=COLORS["sea"] if active else COLORS["muted"])
        self.station_label.configure(text=f"{packet['station']}   |   Tick {packet['tick']}   |   {packet['tick'] / 30:.1f} s mô phỏng")
        fps = (len(self.arrivals) - 1) / max(0.01, self.arrivals[-1] - self.arrivals[0])
        age = max(0, time.monotonic() - packet["time"])
        self.fps_label.configure(text=(
            f"Camera {fps:.0f} fps   |   Trễ {age * 1000:.0f} ms   |   "
            + ("Space: bỏ qua chờ" if damage_pause else "Cảnh báo tự tiếp tục sau 5 giây")
        ))
        if not self.paused and not self.damage_paused and not self.stopping and not self.finished:
            self.status.configure(text="●  Đang khảo sát", fg="#9ee5df")
        self.pause_button.configure(state="normal" if not self.stopping else "disabled")
        if self.smoke_test:
            self.qa["ticks"].append(packet["tick"])

    def snapshot(self, name: str) -> None:
        if self.session:
            self.root.update_idletasks()
            # PrintWindow omits the cross-process DirectX child. Capture our visible client area.
            left, top = self.root.winfo_rootx(), self.root.winfo_rooty()
            image = ImageGrab.grab(bbox=(left, top, left + self.root.winfo_width(),
                                        top + self.root.winfo_height()))
            image.save(self.session / name)

    def qa_tick(self) -> None:
        now = time.monotonic()
        if now - self.qa_started > 90:
            self.qa["timeout"] = True
            self.close()
        if self.packet is None:
            return
        tick = self.packet["tick"]
        self.qa["embedded"] = bool(self.viewport.hwnd)
        if tick > 65 and not self.qa_pause_done:
            self.toggle_pause()
            self.qa_pause_done = True
            self.qa["pause_tick"] = tick
            self.qa_resume_at = now + 1.0
            self.snapshot("dashboard_live.png")
        if self.qa_resume_at and now >= self.qa_resume_at:
            self.qa["pause_delta_ticks"] = tick - self.qa["pause_tick"]
            self.toggle_pause()
            self.qa_resume_at = None
        if self.qa_continue_at and now >= self.qa_continue_at:
            self.snapshot("dashboard_alert.png")
            self.continue_run()
            self.qa["continued"] = True
            self.qa_continue_at = None
        if tick > 260 and not self.stopping:
            self.snapshot("dashboard_resumed.png")
            self.close()

    def poll(self) -> None:
        if self.events:
            while True:
                try:
                    self.handle_event(self.events.get_nowait())
                except Empty:
                    break
        if self.frames:
            latest = None
            while True:
                try:
                    latest = self.frames.get_nowait()
                except Empty:
                    break
            if latest:
                self.render_packet(latest)
        if self.engine_pid and not self.viewport.hwnd and self.worker and self.worker.is_alive():
            try:
                if self.viewport.attach(self.engine_pid):
                    self.placeholder.place_forget()
                    self.pip.lift()
            except Exception as error:
                self.station_label.configure(text=f"Không nhúng được Unreal: {error}")
                self.qa["embed_error"] = str(error)
                self.engine_pid = None
        if self.smoke_test and not self.closing:
            self.qa_tick()
        if self.worker and not self.worker.is_alive() and not self.worker_handled:
            self.worker_handled = True
            self.worker.join(timeout=0)
            self.viewport.detach()
            self.start_button.configure(state="normal")
            self.mode_box.configure(state="readonly")
            self.detector_box.configure(state="readonly")
            for button in (self.pause_button, self.continue_button, self.stop_button):
                button.configure(state="disabled")
            if self.worker.exitcode and "error" not in self.qa:
                self.status.configure(text=f"●  Worker kết thúc lỗi {self.worker.exitcode}", fg="#ffb79b")
            elif not self.finished:
                self.status.configure(text="●  Đã dừng", fg="#bdd1dd")
            self.finished = True
            self.placeholder.configure(text="Phiên đã kết thúc · Bắt đầu khảo sát để chạy phiên mới")
            self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
            self.save_ui_session()
            if self.closing:
                self.finish_close()
                return
        if self.stopping and self.worker and self.worker.is_alive() and time.monotonic() - self.stop_at > 12:
            # Force cleanup only for processes owned by this dashboard session.
            if self.engine_pid:
                try:
                    process = win32api.OpenProcess(1, False, self.engine_pid)
                    win32api.TerminateProcess(process, 1)
                    win32api.CloseHandle(process)
                except Exception as error:
                    self.qa["cleanup_error"] = str(error)
            self.worker.terminate()
            self.worker.join(timeout=1)
            self.qa["forced_shutdown"] = True
        if self.closing and (self.worker is None or not self.worker.is_alive()):
            self.finish_close()
            return
        self.root.after(50, self.poll)

    def close(self) -> None:
        if self.closing:
            return
        self.closing = True
        self.stop()
        if self.worker is None or not self.worker.is_alive():
            self.finish_close()

    def save_ui_session(self) -> None:
        if self.session:
            self.qa["alert_count"] = len(self.alerts)
            self.qa["route_points_recorded"] = len(self.route_map.trail)
            self.qa["worker_exitcode"] = self.worker.exitcode if self.worker else None
            (self.session / "ui_session.json").write_text(json.dumps(self.qa, indent=2), encoding="utf-8")

    def finish_close(self) -> None:
        self.save_ui_session()
        self.viewport.detach()
        for channel in (self.commands, self.frames, self.events):
            if channel:
                channel.close()
        self.root.destroy()

    def validate_smoke_test(self) -> None:
        """Fail the QA command if a live interaction or source-isolation check failed."""
        if not self.session:
            raise RuntimeError("Dashboard QA did not start a session")
        audit = json.loads((self.session / "source_audit.json").read_text(encoding="utf-8"))
        report = self.qa.get("report", {})
        checks = {
            "unreal_embedded": self.qa.get("embedded") is True,
            "live_frames": len(self.qa["ticks"]) > 20 and max(self.qa["ticks"], default=0) > 260,
            # One 12 FPS preview packet may already be queued when the UI sends pause.
            "pause": 0 <= self.qa.get("pause_delta_ticks", -1) <= 3,
            "continue_after_alert": self.qa.get("continued") is True,
            "saved_alert": self.qa.get("alert_count", 0) >= 1,
            "route_updated": self.qa.get("route_points_recorded", 0) > 10,
            "clean_shutdown": self.qa.get("worker_exitcode") == 0 and report.get("stopped_by_user") is True,
            "sources_unchanged": audit["unchanged"] is True,
            "no_errors": not any(self.qa.get(key) for key in ("error", "timeout", "embed_error", "forced_shutdown")),
        }
        (self.session / "qa_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError(f"Dashboard QA failed: {', '.join(failed)}. See {self.session}")
        print(f"Live dashboard QA passed {len(checks)} checks: {self.session}")
