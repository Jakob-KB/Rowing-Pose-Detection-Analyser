# src/models/annotation_preferences.py

from typing import Tuple

from pydantic import BaseModel, conint, confloat

Color = Tuple[
    conint(ge=0, le=255),
    conint(ge=0, le=255),
    conint(ge=0, le=255)
]


class AnnotationPreferences(BaseModel):
    bone_colour: Color
    bone_thickness: conint(gt=0)

    landmark_colour: Color
    landmark_radius: conint(gt=0)

    reference_line_colour: Color
    reference_line_length: conint(gt=0)
    reference_line_thickness: conint(gt=0)
    reference_line_dash_factor: conint(ge=0)

    opacity: confloat(ge=0, le=1)
