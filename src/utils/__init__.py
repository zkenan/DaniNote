"""Utility functions for the sticky notes application."""

import ctypes
import os
import sys
from ctypes import wintypes


def get_base_dir() -> str:
    """Get the application root directory (works in dev and frozen mode)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_dir() -> str:
    """Get the data directory path."""
    data_dir = os.path.join(get_base_dir(), "data")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "notes"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "images"), exist_ok=True)
    return data_dir


def get_config_path() -> str:
    """Get the config file path."""
    return os.path.join(get_data_dir(), "config.json")


def get_db_path() -> str:
    """Get the database file path."""
    return os.path.join(get_data_dir(), "data.db")


class AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(AccentPolicy)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def enable_acrylic_blur(hwnd: int):
    """Enable Windows Acrylic blur effect on a window."""
    accent = AccentPolicy()
    accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = 0x99000000  # ARGB: 60% opacity black

    data = WindowCompositionAttributeData()
    data.Attribute = 19  # WCA_ACCENT_POLICY
    data.SizeOfData = ctypes.sizeof(accent)
    data.Data = ctypes.pointer(accent)

    ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))


def enable_blurbehind(hwnd: int):
    """Enable Windows BlurBehind effect (fallback for older systems)."""
    accent = AccentPolicy()
    accent.AccentState = 3  # ACCENT_ENABLE_BLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = 0

    data = WindowCompositionAttributeData()
    data.Attribute = 19
    data.SizeOfData = ctypes.sizeof(accent)
    data.Data = ctypes.pointer(accent)

    ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
