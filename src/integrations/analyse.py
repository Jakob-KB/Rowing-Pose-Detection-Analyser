# src/scripts/analyze_metrics.py
import cv2
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt


def compute_angle(point1, point2, ref_vector=(-1, 0)):
    """
    Computes the angle (in degrees) between the vector from point2 to point1 and a reference vector.
    """
    dx = point1["x"] - point2["x"]
    dy = point1["y"] - point2["y"]
    norm = math.sqrt(dx ** 2 + dy ** 2)
    if norm == 0:
        return None
    cos_angle = -dx / norm  # using ref_vector (-1, 0)
    cos_angle = max(min(cos_angle, 1), -1)
    return math.degrees(math.acos(cos_angle))