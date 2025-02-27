# src/sessions.py
import json
from datetime import datetime
import shutil
import cv2
import yaml

from src.config import SESSIONS_DIR
from src.data_classes import *

class Session:

    def __init__(self, session_title: str, temp_video_path: Path, overwrite: bool = False) -> None:
        # session identifiers and root path
        self.title = session_title
        self.overwrite = overwrite

        # Session dataclasses
        self.paths = self._build_session_paths(SESSIONS_DIR, session_title)
        self.raw_video_metadata = self._build_raw_video_metadata(temp_video_path)
        self.mediapipe_prefs = self._build_mediapipe_preferences()
        self.annotation_prefs = self._build_annotation_preferences()

        # Session config dict
        self.config: Dict = {}

        # Init methods
        self._setup_session_directory(temp_video_path)
        self._init_config()

    def _setup_session_directory(self, temp_video_path: Path) -> None:
        # Clear the session directory if it already exists and overwrite is true
        if self.paths.session_dir.exists():
            if self.overwrite:
                shutil.rmtree(self.paths.session_dir)
            else:
                logger.error("A session directory with this name already exists.")
                raise FileExistsError()

        # Attempt to create a session directory
        try:
            self.paths.session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create session directory {self.paths.session_dir}: {e}")
            raise Exception()

        # Attempt to clone the video_metadata to the session directory
        try:
            shutil.copy2(temp_video_path, self.paths.raw_video_path)
            logger.info(f"Raw video copied to {self.paths.raw_video_path}")
        except Exception as e:
            logger.error(f"Error while cloning raw video: {e}")
            raise Exception()

        # Delete the temp video_metadata now that raw video_metadata is saved to the session directory
        # os.remove(temp_video_path

    # Handle session config
    def _init_config(self) -> None:
        self.config = {
            "session_title": self.title,
            "creation_date": datetime.now().isoformat(),
            "overwrite": self.overwrite,

            "paths": {
                "session_dir": str(self.paths.session_dir.resolve()),
                "raw_video_path": str(self.paths.raw_video_path.resolve()),
                "annotated_video_path": str(self.paths.annotated_video_path.resolve()),
                "landmark_data_path": str(self.paths.landmark_data_path.resolve()),
                "analysis_data_path": str(self.paths.analysis_data_path.resolve()),
                "session_config_path": str(self.paths.session_config_path.resolve())
            },

            "video_metadata": {
                "width": self.raw_video_metadata.width,
                "height": self.raw_video_metadata.height,
                "fps": self.raw_video_metadata.fps,
                "total_frames": self.raw_video_metadata.total_frames
            },

            "mediapipe": {
                "model_complexity": self.mediapipe_prefs.model_complexity,
                "smooth_landmarks": self.mediapipe_prefs.smooth_landmarks,
                "min_detection_confidence": self.mediapipe_prefs.min_detection_confidence,
                "min_tracking_confidence": self.mediapipe_prefs.min_tracking_confidence
            },

            "annotation": {
                "opacity": self.annotation_prefs.opacity,
                "bone": {
                    "colour": list(self.annotation_prefs.BonePrefs.colour),  # tuple -> list
                    "thickness": self.annotation_prefs.BonePrefs.thickness
                },
                "landmark": {
                    "colour": list(self.annotation_prefs.LandmarkPrefs.colour),
                    "radius": self.annotation_prefs.LandmarkPrefs.radius
                },
                "reference_line": {
                    "length": self.annotation_prefs.ReferenceLinePrefs.length,
                    "colour": list(self.annotation_prefs.ReferenceLinePrefs.colour),
                    "thickness": self.annotation_prefs.ReferenceLinePrefs.thickness,
                    "dash_factor": self.annotation_prefs.ReferenceLinePrefs.dash_factor
                }
            }
        }
        self.save_config()

    def save_config(self) -> None:
        try:
            with open(self.paths.session_config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.paths.session_config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.paths.session_config_path}: {e}")
            raise

    # Handle landmark data
    def save_landmark_data_to_session(self, landmark_data: LandmarkData) -> None:
        data_dict = landmark_data.to_dict()

        try:
            with open(self.paths.landmark_data_path, "w") as f:
                yaml.safe_dump(data_dict, f, default_flow_style=False)
            logger.info(f"Landmark data saved to {self.paths.landmark_data_path}")
        except Exception as e:
            logger.error(f"Error saving landmark data: {e}")
            raise Exception()

    def load_landmark_data_from_session(self) -> LandmarkData:

        if not self.paths.landmark_data_path.exists():
            raise FileNotFoundError(f"Landmark file not found at {self.paths.landmark_data_path}")

        try:
            with open(self.paths.landmark_data_path, "r") as f:
                data_dict = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading landmark data: {e}")
            raise

        # Convert the dict into a LandmarkData object
        landmark_data = LandmarkData.from_dict(data_dict)
        logger.info(f"Landmark data loaded from {self.paths.landmark_data_path}")
        return landmark_data

    # Handle session specific dataclasses
    @staticmethod
    def _build_raw_video_metadata(raw_video_path: Path) -> VideoMetadata:

        cap = cv2.VideoCapture(str(raw_video_path))
        if not cap.isOpened():
            msg = f"Could not open video file: {raw_video_path}"
            logger.error(msg)
            raise ValueError(msg)

        # Retrieve properties
        video_data_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_data_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_data_fps = cap.get(cv2.CAP_PROP_FPS)
        video_data_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        cap.release()
        return VideoMetadata(
            width=video_data_width,
            height=video_data_height,
            fps=video_data_fps,
            total_frames=video_data_total_frames
        )

    @staticmethod
    def _build_session_paths(base_dir: Path, session_title: str) -> SessionPaths:
        session_dir = base_dir / session_title
        return SessionPaths(
            session_dir=session_dir,
            raw_video_path=session_dir / "raw.mp4",
            annotated_video_path=session_dir / "annotated.mp4",
            landmark_data_path=session_dir / "landmarks.yaml",
            analysis_data_path=session_dir / "analysis.yaml",
            session_config_path=session_dir / "session_config.json"
        )

    @staticmethod
    def _build_mediapipe_preferences():
        return MediapipePreferences()

    @staticmethod
    def _build_annotation_preferences():
        return AnnotationPrefs()

    # -----------------------
    # Loading Existing Session
    # -----------------------
    @classmethod
    def load_existing_session(cls, session_dir: Path) -> "Session":
        """
        Load session_config.json, restore the session object with the same
        data classes and paths as used originally.
        """
        config_file_path = session_dir / "session_config.json"
        if not config_file_path.exists():
            raise FileNotFoundError(f"No config file found at {config_file_path}")

        try:
            with open(config_file_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_file_path}: {e}")
            raise

        # Create an instance without calling __init__
        instance = cls.__new__(cls)
        instance._apply_config(config)
        return instance

    def _apply_config(self, config: Dict) -> None:
        """
        Re-construct the session's fields (paths, metadata, etc.) from a loaded config dict.
        This is effectively the inverse of _build_config_dict.
        """
        self.title = config.get("session_title")
        if not self.title:
            raise ValueError("No 'session_title' in config")

        self.overwrite = config.get("overwrite", False)

        # Rebuild the paths
        paths_info = config.get("paths", {})
        self.paths = SessionPaths(
            session_dir=Path(paths_info["session_dir"]),
            raw_video_path=Path(paths_info["raw_video_path"]),
            annotated_video_path=Path(paths_info["annotated_video_path"]),
            landmark_data_path=Path(paths_info["landmark_data_path"]),
            analysis_data_path=Path(paths_info["analysis_data_path"]),
            session_config_path=Path(paths_info["config_file_path"])
        )

        # Rebuild video metadata
        vid_info = config.get("video_metadata", {})
        self.raw_video_metadata = VideoMetadata(
            width=vid_info.get("width", cfg.video.width),
            height=vid_info.get("height", cfg.video.height),
            fps=vid_info.get("fps", cfg.video.fps),
            total_frames=vid_info.get("total_frames")
        )

        # Rebuild mediapipe prefs
        mp_info = config.get("mediapipe", {})
        self.mediapipe_prefs = MediapipePreferences(
            model_complexity=mp_info.get("model_complexity", cfg.mediapipe.model_complexity),
            smooth_landmarks=mp_info.get("smooth_landmarks", cfg.mediapipe.smooth_landmarks),
            min_detection_confidence=mp_info.get("min_detection_confidence", cfg.mediapipe.min_detection_confidence),
            min_tracking_confidence=mp_info.get("min_tracking_confidence", cfg.mediapipe.min_tracking_confidence)
        )

        # Rebuild annotation prefs
        ann_info = config.get("annotation", {})
        self.annotation_prefs = AnnotationPrefs(
            opacity=ann_info.get("opacity", cfg.annotation_prefs.opacity)
        )
        # For the nested ones, create them individually and store them on self.annotation_prefs
        bone_info = ann_info.get("bone", {})
        self.annotation_prefs.BonePrefs = AnnotationPrefs.BonePrefs(
            colour=tuple(bone_info.get("colour", cfg.annotation_prefs.bone.colour)),
            thickness=bone_info.get("thickness", cfg.annotation_prefs.bone.thickness)
        )

        landmark_info = ann_info.get("landmark", {})
        self.annotation_prefs.LandmarkPrefs = AnnotationPrefs.LandmarkPrefs(
            colour=tuple(landmark_info.get("colour", cfg.annotation_prefs.landmark.colour)),
            radius=landmark_info.get("radius", cfg.annotation_prefs.landmark.radius)
        )

        ref_info = ann_info.get("reference_line", {})
        self.annotation_prefs.ReferenceLinePrefs = AnnotationPrefs.ReferenceLinePrefs(
            length=ref_info.get("length", cfg.annotation_prefs.reference_line.length),
            colour=tuple(ref_info.get("colour", cfg.annotation_prefs.reference_line.colour)),
            thickness=ref_info.get("thickness", cfg.annotation_prefs.reference_line.thickness),
            dash_factor=ref_info.get("dash_factor", cfg.annotation_prefs.reference_line.dash_factor)
        )

        self.config = config
        self.session_path = self.paths.session_dir
        logger.info(f"Session {self.title} reloaded with annotation prefs: {self.annotation_prefs}")

        self.config = config

        # Make sure you store self.session_path or any other attributes if needed
        self.session_path = self.paths.session_dir

        logger.info(f"Session {self.title} loaded from config")

# Example usage:
if __name__ == "__main__":
    from src.config import DATA_DIR

    title = "athlete_1"
    original_video = DATA_DIR / "videos" / f"{title}.mp4"

    # Create a new session with overwrite option (set to False by default)
    new_session = Session(title, original_video, overwrite=True)
    print("New session config:", new_session.config)

    load_existing_session = False

    if load_existing_session:
        # Load an existing session
        existing_session = SESSIONS_DIR / title
        loaded_session = Session.load_existing_session(existing_session)
        print("Loaded session config:", loaded_session.config)