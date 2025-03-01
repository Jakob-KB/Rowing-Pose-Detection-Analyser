# src/models/annotation_preferences.py
from pydantic import BaseModel
from typing import Tuple

class AnnotationPreferences(BaseModel):
    bone_colour: Tuple[int, int, int]
    bone_thickness: int

    landmark_colour: Tuple[int, int, int]
    landmark_radius: int

    reference_line_colour: Tuple[int, int, int]
    reference_line_length: int
    reference_line_thickness: int
    reference_line_dash_factor: int

    opacity: float