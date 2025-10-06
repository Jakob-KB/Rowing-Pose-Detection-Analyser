import webview
from pathlib import Path

if __name__ == "__main__":
    html_filename = "simple_prog.html"
    html_file = (Path(__file__).parent / html_filename).resolve(strict=True)
    webview.create_window("My App", html_file.as_uri())
    webview.start()
