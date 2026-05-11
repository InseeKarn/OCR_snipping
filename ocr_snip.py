import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox

try:
    from PIL import ImageGrab
except ImportError:
    raise ImportError("Pillow is required. Install with: pip install Pillow")

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )
except ImportError:
    raise ImportError("pytesseract is required. Install with: pip install pytesseract")

try:
    import pyperclip
except ImportError:
    raise ImportError("pyperclip is required. Install with: pip install pyperclip")

try:
    import keyboard
except ImportError:
    raise ImportError("keyboard is required. Install with: pip install keyboard")

DEFAULT_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def locate_tesseract():
    if os.environ.get("TESSERACT_CMD"):
        return os.environ["TESSERACT_CMD"]

    for path in DEFAULT_TESSERACT_PATHS:
        if os.path.isfile(path):
            return path

    return None


def configure_tesseract():
    path = locate_tesseract()
    if path:
        pytesseract.pytesseract.tesseract_cmd = path
    else:
        print("Warning: Tesseract executable not found. Please install Tesseract OCR and set TESSERACT_CMD or use one of the default install paths.")


def capture_region():
    overlay = tk.Toplevel(root)
    overlay.withdraw()
    overlay.overrideredirect(True)

    screen_width = overlay.winfo_screenwidth()
    screen_height = overlay.winfo_screenheight()

    overlay.geometry(f"{screen_width}x{screen_height}+0+0")

    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.30)
    overlay.config(bg="black")

    canvas = tk.Canvas(overlay, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x = tk.IntVar(value=0)
    start_y = tk.IntVar(value=0)
    rect_id = None

    def on_button_press(event):
        start_x.set(event.x_root)
        start_y.set(event.y_root)
        nonlocal rect_id
        rect_id = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="white", width=2)

    def on_mouse_drag(event):
        x0, y0 = start_x.get(), start_y.get()
        x1, y1 = event.x_root, event.y_root
        canvas.coords(rect_id, x0 - overlay.winfo_x(), y0 - overlay.winfo_y(), x1 - overlay.winfo_x(), y1 - overlay.winfo_y())

    def on_button_release(event):
        overlay.destroy()
        x0, y0 = start_x.get(), start_y.get()
        x1, y1 = event.x_root, event.y_root
        x1, x0 = max(x0, x1), min(x0, x1)
        y1, y0 = max(y0, y1), min(y0, y1)
        if x1 - x0 < 10 or y1 - y0 < 10:
            print("Selection too small. Try again.")
            return

        try:
            screenshot = ImageGrab.grab(bbox=(x0, y0, x1, y1))
            ocr_text = run_ocr(screenshot)
            if not ocr_text.strip():
                ocr_text = "(ไม่พบข้อความจากภาพ)"
            show_text_editor(ocr_text)
        except Exception as exc:
            messagebox.showerror("OCR Error", f"ไม่สามารถจับภาพหรืออ่านข้อความได้:\n{exc}")

    canvas.bind("<ButtonPress-1>", on_button_press)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_button_release)

    overlay.deiconify()
    overlay.focus_force()
    overlay.grab_set()
    overlay.wait_window()


def run_ocr(image):
    languages = "eng+tha"
    try:
        return pytesseract.image_to_string(image, lang=languages)
    except pytesseract.pytesseract.TesseractError:
        return pytesseract.image_to_string(image)
    except Exception as exc:
        raise RuntimeError(f"OCR failed: {exc}")


def show_text_editor(text):
    editor = tk.Toplevel(root)
    editor.title("OCR Result")
    editor.geometry("800x520")
    editor.attributes("-topmost", True)

    text_widget = tk.Text(editor, wrap=tk.WORD, font=("Segoe UI", 11))
    text_widget.insert("1.0", text)
    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    button_frame = tk.Frame(editor)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    def copy_text():
        content = text_widget.get("1.0", tk.END).strip()
        pyperclip.copy(content)
        messagebox.showinfo("Copied", "ข้อความถูกคัดลอกไปที่ clipboard แล้ว")

    copy_button = tk.Button(button_frame, text="Copy to Clipboard", command=copy_text)
    copy_button.pack(side=tk.LEFT, padx=(0, 6))

    close_button = tk.Button(button_frame, text="Close", command=editor.destroy)
    close_button.pack(side=tk.LEFT)

    def bind_text_shortcuts(widget):
        widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>") or "break")
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>") or "break")
        widget.bind("<Control-x>", lambda e: widget.event_generate("<<Cut>>") or "break")
        widget.bind("<Control-a>", lambda e: widget.tag_add("sel", "1.0", "end") or "break")

    bind_text_shortcuts(text_widget)
    text_widget.focus_set()

    editor.focus_force()
    editor.grab_set()
    editor.wait_window()


def on_hotkey():
    if not selection_event.is_set():
        selection_event.set()


def poll_hotkey():
    if selection_event.is_set():
        selection_event.clear()
        capture_region()
    root.after(100, poll_hotkey)


def ensure_keyboard_registered():
    try:
        keyboard.add_hotkey("ctrl+shift+s", on_hotkey)
        keyboard.add_hotkey("ctrl+shift+q", lambda: root.quit())
    except Exception as exc:
        messagebox.showerror("Hotkey Error", f"ไม่สามารถลงทะเบียน hotkey ได้:\n{exc}")
        sys.exit(1)


if __name__ == "__main__":
    configure_tesseract()

    root = tk.Tk()
    root.withdraw()
    root.title("OCR Snip")

    selection_event = threading.Event()
    ensure_keyboard_registered()

    print("Ready. Press Ctrl+Shift+S to snip a region, or Ctrl+Shift+Q to quit.")
    root.after(100, poll_hotkey)
    root.mainloop()
