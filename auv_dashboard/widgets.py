"""Small native Tk widgets for live camera tiles and the measured route."""
from __future__ import annotations

from io import BytesIO
from math import cos, hypot, radians, sin
import tkinter as tk

from PIL import Image, ImageTk

COLORS = {
    "bg": "#edf3f5", "panel": "#ffffff", "ink": "#15384b", "muted": "#637b88",
    "sea": "#087f8c", "line": "#d1e0e5", "navy": "#102f46", "amber": "#b85a14",
}
FONT = "Segoe UI"


class CameraTile(tk.Canvas):
    def __init__(self, parent: tk.Misc, placeholder: str = "Chờ tín hiệu camera", **kwargs: object) -> None:
        super().__init__(parent, bg=COLORS["navy"], width=1, height=1, highlightthickness=0, **kwargs)
        self.placeholder = placeholder
        self.source: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.image_id = self.create_image(0, 0, anchor="center")
        self.text_id = self.create_text(0, 0, text=placeholder, fill="#a9c4d0", font=(FONT, 10))
        self.bind("<Configure>", lambda _event: self.render())

    def set_frame(self, data: bytes) -> None:
        with Image.open(BytesIO(data)) as image:
            self.source = image.convert("RGB")
        self.render()

    def render(self) -> None:
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        self.coords(self.text_id, width / 2, height / 2)
        if self.source is None or width < 5 or height < 5:
            return
        source = self.source.copy()
        source.thumbnail((width, height), Image.Resampling.BILINEAR)
        self.photo = ImageTk.PhotoImage(source)
        self.itemconfigure(self.image_id, image=self.photo)
        self.itemconfigure(self.text_id, text="")
        self.coords(self.image_id, width / 2, height / 2)

    def clear(self) -> None:
        self.source = None
        self.photo = None
        self.itemconfigure(self.image_id, image="")
        self.itemconfigure(self.text_id, text=self.placeholder)


def project_3d(point: tuple[float, float, float], center: tuple[float, float, float],
               yaw: float, pitch: float, scale: float,
               origin: tuple[float, float]) -> tuple[float, float]:
    """Project a world XYZ point onto the lightweight route canvas."""
    dx, dy, dz = (point[index] - center[index] for index in range(3))
    horizontal = dx * cos(yaw) - dy * sin(yaw)
    depth = dx * sin(yaw) + dy * cos(yaw)
    vertical = dz * cos(pitch) - depth * sin(pitch)
    return origin[0] + horizontal * scale, origin[1] - vertical * scale


class RouteMap(tk.Canvas):
    def __init__(self, parent: tk.Misc, route: list, **kwargs: object) -> None:
        super().__init__(parent, bg="#f3f8fa", highlightthickness=0, **kwargs)
        self.route = route
        self.route_points = [tuple(float(value) for value in pose[:3]) for _, pose in route]
        self.trail: list[tuple[float, float, float]] = []
        self.alerts: list[tuple[float, float, float]] = []
        self.position: tuple[float, float, float] | None = None
        self.yaw = 0.0
        self.view_yaw = radians(-32)
        self.view_pitch = radians(34)
        self.zoom = 1.0
        self.drag_anchor: tuple[int, int] | None = None
        world_points = self.route_points + [
            (-22.0, -13.0, -12.5), (22.0, 7.0, -12.5),
            (-10.0, -6.5, 1.0), (10.0, -6.5, 1.0),
        ]
        self.center = tuple(
            (min(point[index] for point in world_points) + max(point[index] for point in world_points)) / 2
            for index in range(3)
        )
        self.bind("<Configure>", lambda _event: self.render())
        self.bind("<ButtonPress-1>", self.begin_orbit)
        self.bind("<B1-Motion>", self.orbit)
        self.bind("<ButtonRelease-1>", lambda _event: setattr(self, "drag_anchor", None))
        self.bind("<MouseWheel>", self.wheel_zoom)
        self.bind("<Double-Button-1>", lambda _event: self.reset_view())
        self.configure(cursor="fleur")

    def begin_orbit(self, event: tk.Event) -> None:
        self.drag_anchor = (event.x, event.y)

    def orbit(self, event: tk.Event) -> None:
        if self.drag_anchor is None:
            return
        dx, dy = event.x - self.drag_anchor[0], event.y - self.drag_anchor[1]
        self.drag_anchor = (event.x, event.y)
        self.view_yaw += dx * 0.012
        self.view_pitch = max(radians(12), min(radians(75), self.view_pitch - dy * 0.01))
        self.render()

    def wheel_zoom(self, event: tk.Event) -> None:
        self.zoom = max(0.65, min(2.8, self.zoom * (1.12 if event.delta > 0 else 1 / 1.12)))
        self.render()

    def reset_view(self) -> None:
        self.view_yaw, self.view_pitch, self.zoom = radians(-32), radians(34), 1.0
        self.render()

    def clear_run(self) -> None:
        self.trail.clear()
        self.alerts.clear()
        self.position = None
        self.render()

    def add_alert(self, position: list[float]) -> None:
        point = tuple(float(value) for value in position[:3])
        if point not in self.alerts:
            self.alerts.append(point)
        self.render()

    def update_position(self, position: list[float], yaw: float) -> None:
        point = tuple(float(value) for value in position[:3])
        if not self.trail or sum((point[index] - self.trail[-1][index]) ** 2 for index in range(3)) > 0.02:
            self.trail.append(point)
        self.position, self.yaw = point, yaw
        self.render()

    def projection(self) -> tuple[float, tuple[float, float]]:
        width, height = max(40, self.winfo_width()), max(40, self.winfo_height())
        bounds = self.route_points + [
            (-22.0, -13.0, -12.5), (22.0, -13.0, -12.5),
            (-22.0, 7.0, -12.5), (22.0, 7.0, -12.5),
            (-10.0, -6.5, 1.0), (10.0, -6.5, 1.0),
        ]
        raw = [project_3d(point, self.center, self.view_yaw, self.view_pitch, 1.0, (0.0, 0.0))
               for point in bounds]
        min_x, max_x = min(point[0] for point in raw), max(point[0] for point in raw)
        min_y, max_y = min(point[1] for point in raw), max(point[1] for point in raw)
        scale = min((width - 24) / max(1.0, max_x - min_x),
                    (height - 38) / max(1.0, max_y - min_y)) * self.zoom
        origin = (width / 2 - (min_x + max_x) * scale / 2,
                  height / 2 - (min_y + max_y) * scale / 2 - 3)
        return scale, origin

    def project(self, point: tuple[float, float, float], scale: float,
                origin: tuple[float, float]) -> tuple[float, float]:
        return project_3d(point, self.center, self.view_yaw, self.view_pitch, scale, origin)

    def line(self, points: list[tuple[float, float, float]], scale: float,
             origin: tuple[float, float], **kwargs: object) -> None:
        coordinates = [value for point in points for value in self.project(point, scale, origin)]
        if len(coordinates) >= 4:
            self.create_line(*coordinates, **kwargs)

    def render(self) -> None:
        self.delete("all")
        scale, origin = self.projection()
        for x in range(-20, 21, 5):
            self.line([(x, -13, -12.5), (x, 7, -12.5)], scale, origin,
                      fill="#dce9ee", width=1)
        for y in range(-10, 6, 5):
            self.line([(-22, y, -12.5), (22, y, -12.5)], scale, origin,
                      fill="#dce9ee", width=1)

        self.line([(-18.01, 0, -10.3), (15.11, 0, -10.3)], scale, origin,
                  fill="#a9c1cb", width=7)
        self.line([(-18.01, 0, -10.3), (15.11, 0, -10.3)], scale, origin,
                  fill="#d8e6eb", width=2)
        for x in (-10, 10):
            self.line([(x, -6.5, -12.5), (x, -6.5, 1.0)], scale, origin,
                      fill="#9fb9c4", width=9)
            self.line([(x, -6.5, -12.5), (x, -6.5, 1.0)], scale, origin,
                      fill="#d5e4e9", width=2)
        self.line(self.route_points, scale, origin, fill="#769aaa", dash=(4, 4), width=1)
        self.line(self.trail, scale, origin, fill="#11a8b3", width=3)

        for index, alert in enumerate(self.alerts, start=1):
            x, y = self.project(alert, scale, origin)
            self.create_oval(x - 6, y - 6, x + 6, y + 6, fill="#ff7a45", outline="white", width=2)
            self.create_text(x + 8, y - 8, text=str(index), fill="#a33c18", anchor="sw",
                             font=(FONT, 8, "bold"))
        if self.position:
            x, y = self.project(self.position, scale, origin)
            heading = radians(self.yaw)
            forward = (self.position[0] + cos(heading), self.position[1] + sin(heading), self.position[2])
            fx, fy = self.project(forward, scale, origin)
            length = max(0.001, hypot(fx - x, fy - y))
            dx, dy = (fx - x) / length, (fy - y) / length
            points = (x + dx * 10, y + dy * 10, x - dx * 6 - dy * 5, y - dy * 6 + dx * 5,
                      x - dx * 4, y - dy * 4, x - dx * 6 + dy * 5, y - dy * 6 - dx * 5)
            self.create_polygon(*points, fill="#f08b47", outline="white", width=1)
        self.create_text(10, 9, text="Kéo: xoay · Cuộn: zoom · Nhấp đúp: đặt lại",
                         fill=COLORS["muted"], anchor="nw", font=(FONT, 8))
        self.create_text(10, self.winfo_height() - 8, text="━ Z   ━ X   ━ Y",
                         fill=COLORS["sea"], anchor="sw", font=(FONT, 8))
