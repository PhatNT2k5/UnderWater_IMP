import threading

import cv2
import os
from pathlib import Path

os.environ["HOLODECKPATH"] = str(
    Path(__file__).resolve().parent / "worlds"
)

import holoocean
import numpy as np
from pynput import keyboard


# Các phím đang được giữ
pressed_keys = set()
key_lock = threading.Lock()
stop_event = threading.Event()

FORCE = 25  # Giảm xuống nếu robot di chuyển quá mạnh


def on_press(key):
    if key == keyboard.Key.esc:
        stop_event.set()
        return False

    char = getattr(key, "char", None)
    if char:
        with key_lock:
            pressed_keys.add(char.lower())


def on_release(key):
    char = getattr(key, "char", None)
    if char:
        with key_lock:
            pressed_keys.discard(char.lower())


def get_command():
    with key_lock:
        keys = pressed_keys.copy()

    command = np.zeros(8)

    # Lên / xuống
    vertical = int("i" in keys) - int("k" in keys)
    command[:4] += vertical * FORCE

    # Tiến / lùi
    forward = int("w" in keys) - int("s" in keys)
    command[4:] += forward * FORCE

    # Sang trái / sang phải
    sideways = int("a" in keys) - int("d" in keys)
    command[[4, 6]] += sideways * FORCE
    command[[5, 7]] -= sideways * FORCE

    # Xoay trái / xoay phải
    yaw = int("j" in keys) - int("l" in keys)
    command[[4, 7]] += yaw * FORCE
    command[[5, 6]] -= yaw * FORCE

    return command


def main():
    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
    )

    print("Dang mo mo phong Dam, vui long cho...")
    print("W/S: tien/lui | A/D: sang ngang")
    print("I/K: len/xuong | J/L: xoay | ESC: thoat")

    try:
        with holoocean.make("Dam-HoveringCamera") as env:
            listener.start()
            print("Mo phong da san sang!")

            while not stop_event.is_set():
                env.act("auv0", get_command())
                state = env.tick()

                if "LeftCamera" in state:
                    frame = state["LeftCamera"][:, :, :3].copy()

                    # Them xu ly anh cua nhom tai day
                    cv2.imshow("Robot Camera", frame)

                if cv2.waitKey(1) & 0xFF == 27:
                    stop_event.set()

    finally:
        listener.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()