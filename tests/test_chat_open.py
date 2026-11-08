from pathlib import Path

import cv2
import numpy as np

from bot.gamesettings import chat_open

D = Path(__file__).parent.parent / "fixtures" / "chat"


def frame(name):  # fixtures keep the bottom-left crop (500:640, 0:300) of a 1280x720 frame
    f = np.zeros((720, 1280, 3), np.uint8)
    f[500:640, 0:300] = cv2.imread(str(D / f"{name}.png"))
    return f


def test_linux_chat_open():
    assert chat_open(frame("chat_open_linux"))


def test_linux_chat_closed():
    assert not chat_open(frame("chat_closed_linux"))
