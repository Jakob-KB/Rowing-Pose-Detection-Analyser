# src/models/annotation_preferences.py

from typing import Tuple

from pydantic import BaseModel, conint, confloat

from src.config import cfg

Color = Tuple[
    conint(ge=0, le=255),
    conint(ge=0, le=255),
    conint(ge=0, le=255)
]


class AnnotationPreferences(BaseModel):
    bone_colour: Color = tuple(cfg.session.annotation_preferences.bone_colour)
    bone_thickness: conint(gt=0) = cfg.session.annotation_preferences.bone_thickness

    landmark_colour: Color = tuple(cfg.session.annotation_preferences.landmark_colour)
    landmark_radius: conint(gt=0) = cfg.session.annotation_preferences.landmark_radius

    reference_line_colour: Color = tuple(cfg.session.annotation_preferences.reference_line_colour)
    reference_line_length: conint(gt=0) = cfg.session.annotation_preferences.reference_line_length
    reference_line_thickness: conint(gt=0) = cfg.session.annotation_preferences.reference_line_thickness
    reference_line_dash_factor: conint(ge=0) = cfg.session.annotation_preferences.reference_line_dash_factor

    opacity: confloat(ge=0, le=1) = cfg.session.annotation_preferences.opacity
