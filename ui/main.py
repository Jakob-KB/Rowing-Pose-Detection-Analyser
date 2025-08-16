import webview

def main():
    webview.create_window("Hello World", "https://example.com")
    webview.start()

if __name__ == '__main__':
    main()