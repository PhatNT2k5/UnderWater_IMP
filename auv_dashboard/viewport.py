"""Embed only the Unreal game window belonging to this dashboard session."""
from __future__ import annotations

import tkinter as tk

import win32con
import win32gui
import win32process


class UnrealViewport:
    def __init__(self, host: tk.Frame) -> None:
        self.host = host
        self.pid: int | None = None
        self.hwnd: int | None = None
        self.original_style: int | None = None

    def attach(self, pid: int) -> bool:
        self.pid = pid
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            return True
        windows: list[int] = []

        def collect(hwnd: int, _context: object) -> None:
            if win32process.GetWindowThreadProcessId(hwnd)[1] != pid:
                return
            if win32gui.GetClassName(hwnd) == "UnrealWindow" and win32gui.IsWindowVisible(hwnd):
                windows.append(hwnd)

        win32gui.EnumWindows(collect, None)
        if not windows:
            return False
        self.hwnd = max(windows, key=lambda handle: self._area(handle))
        self.original_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
        style = self.original_style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_POPUP)
        style |= win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_CLIPSIBLINGS
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)
        win32gui.SetParent(self.hwnd, self.host.winfo_id())
        self.resize()
        return True

    @staticmethod
    def _area(hwnd: int) -> int:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        return (right - left) * (bottom - top)

    def resize(self) -> None:
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            win32gui.SetWindowPos(
                self.hwnd, 0, 0, 0, max(1, self.host.winfo_width()), max(1, self.host.winfo_height()),
                win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED,
            )

    def detach(self) -> None:
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            win32gui.SetParent(self.hwnd, 0)
            if self.original_style is not None:
                win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, self.original_style)
        self.hwnd = None
        self.pid = None
