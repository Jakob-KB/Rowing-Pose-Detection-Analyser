# src/utils/file_handler.py
import shutil
from pathlib import Path
from typing import List
import mimetypes
import os

from src.config import logger

def check_path_is_clear(path: Path, var_name: str = "File", overwrite: bool = False):
    path_exists: bool = path.exists()

    if path_exists is True:
        if overwrite is True:
            if path.is_file():
                os.remove(path)
            elif path.is_dir():
                shutil.rmtree(path)
            logger.info(f"'{var_name}' was found at '{path}'. Deleting it so it can be overwritten.")
            return True, ""
        elif overwrite is False:
            msg = f"'{var_name}' was found at '{path}'."
            return False, msg
    elif path_exists is False:
        return True, ""

    return True, ""

def check_path_exists(path: Path, var_name: str = "File", delete_if_found: bool = False) -> (bool, str):
    file_exists: bool = path.exists()

    if file_exists is False:
        msg = f"Unable to find '{var_name}' at '{path}'"
        return False, msg
    elif file_exists is True:
        return True, ""
