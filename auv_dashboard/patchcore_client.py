"""Communicate with the separate PatchCore Python environment."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from queue import Empty, Queue
import subprocess
from threading import Thread
from typing import TextIO

import cv2
import numpy as np


class PatchCoreClient:
    def __init__(self, root: Path, session: Path, model_dir: Path,
                 reference_dataset: Path, thresholds_file: Path,
                 python_executable: Path | None = None, roi_mode: str = "geometry") -> None:
        executable = python_executable or root / ".venv-patchcore/Scripts/python.exe"
        if not executable.is_file():
            raise FileNotFoundError(f"PatchCore Python not found: {executable}")
        if not thresholds_file.is_file():
            raise FileNotFoundError(f"Calibrated PatchCore thresholds not found: {thresholds_file}")
        self._stderr: TextIO = (session / "patchcore_worker.log").open("w", encoding="utf-8")
        self._responses: Queue[dict | BaseException] = Queue()
        command = [str(executable), "-u", "-m", "auv_inspection.patchcore_data.live_service",
                   str(model_dir), str(reference_dataset), str(thresholds_file),
                   "--roi-mode", roi_mode]
        try:
            self.process = subprocess.Popen(
                command, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self._stderr, text=True, encoding="utf-8", bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            self._stderr.close()
            raise
        self._reader = Thread(target=self._read_responses, daemon=True)
        self._reader.start()
        try:
            ready = self._receive(timeout=90.0)
            if ready.get("type") != "ready":
                raise RuntimeError(f"PatchCore worker did not become ready: {ready}")
        except Exception:
            self.close()
            raise

    def _read_responses(self) -> None:
        try:
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self._responses.put(json.loads(line))
            self._responses.put(RuntimeError(
                f"PatchCore worker exited with code {self.process.poll()}"))
        except Exception as error:
            self._responses.put(error)

    def _receive(self, timeout: float) -> dict:
        try:
            result = self._responses.get(timeout=timeout)
        except Empty as error:
            raise TimeoutError("PatchCore worker response timed out") from error
        if isinstance(result, BaseException):
            raise RuntimeError("PatchCore worker failed") from result
        if result.get("type") == "error":
            raise RuntimeError(f"PatchCore worker error: {result.get('message')}")
        return result

    def analyze(self, frame: np.ndarray, tick: int, category: str,
                station: str, position_m: list[float], yaw_deg: float,
                timeout: float = 5.0) -> dict:
        if self.process.poll() is not None:
            raise RuntimeError(f"PatchCore worker exited with code {self.process.returncode}")
        success, encoded = cv2.imencode(".png", frame[:, :, :3])
        if not success:
            raise OSError("Could not encode camera PNG")
        request = {"type": "analyze", "tick": tick, "category": category,
                   "station": station, "position_m": position_m, "yaw_deg": yaw_deg,
                   "camera_png_b64": base64.b64encode(encoded).decode("ascii")}
        assert self.process.stdin is not None
        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            response = self._receive(timeout)
        except Exception:
            self.close()
            raise
        if response.get("tick") != tick or response.get("category") != category:
            self.close()
            raise RuntimeError("PatchCore worker returned a mismatched frame result")
        return response

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                if self.process.stdin is not None:
                    self.process.stdin.write('{"type":"stop"}\n')
                    self.process.stdin.flush()
                self.process.wait(timeout=2.0)
            except (BrokenPipeError, OSError, ValueError, subprocess.TimeoutExpired):
                self.process.terminate()
                try:
                    self.process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2.0)
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        if self.process.stdout is not None and not self.process.stdout.closed:
            self.process.stdout.close()
        if not self._stderr.closed:
            self._stderr.close()


def decode_image(encoded: str) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8),
                         cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("PatchCore worker returned an invalid image")
    return image
