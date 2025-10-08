import logging
import os
import threading
import queue
from pathlib import Path

import pystray
from PIL import Image

class SystemTrayIcon:
    """Class to manage the system tray icon and UI interactions."""

    def __init__(self, app_name: str, icon_path: Path, status_queue: queue.Queue, stop_event: threading.Event, downloads_path: Path):
        self.app_name = app_name
        self.icon_path = icon_path
        self.status_queue = status_queue
        self.stop_event = stop_event
        self.downloads_path = downloads_path

        self.icon = pystray.Icon(self.app_name)
        self.icon.icon = self._create_image()
        self.icon.title = "Orionis Auto Sort"
        self.icon.menu = self._create_menu()

        self.status_thread = threading.Thread(target=self._process_status_queue, daemon=True)

    def _create_image(self):
        """Create image object from the icon file."""
        try:
            return Image.open(self.icon_path)
        except Exception as e:
            logging.error("❌ Error loading icon image: %s. Using default.", e)
            return Image.new('RGB', (64, 64), color=(73, 134, 232))

    def _create_menu(self):
        """Create the context menu for the system tray icon."""
        return pystray.Menu(
            pystray.MenuItem('Status: Running', None, enabled=False),
            pystray.MenuItem('Open Downloads Folder', self._open_downloads),
            pystray.MenuItem('Exit', self._exit_app)
        )

    def _open_downloads(self):
        """Open the user's Downloads folder."""
        try:
            os.startfile(str(self.downloads_path))
        except Exception as e:
            logging.error("❌ Error opening downloads folder: %s", e)
            self.show_notification("Error", f"Could not open folder: {e}")

    def _exit_app(self):
        """Signal the application to exit."""
        logging.info("🛑 Exit requested from tray icon.")
        self.stop_event.set()
        self.icon.stop()

    def _process_status_queue(self):
        """Process messages from the status queue to show notifications."""
        while not self.stop_event.is_set():
            try:
                message = self.status_queue.get(timeout=1)
                if message:
                    title = message.get('title', 'Notification')
                    text = message.get('text', '')
                    self.show_notification(title, text)
                self.status_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logging.error("❌ Error in status queue processing: %s", e)

    def show_notification(self, title: str, message: str):
        """Display a desktop notification."""
        if self.icon.visible:
            self.icon.notify(message, title)

    def run(self):
        """Run the system tray icon in the main thread."""
        logging.info("🚀 System tray icon is running.")
        self.status_thread.start()
        self.icon.run()

    def stop(self):
        """Stop the system tray icon."""
        logging.info("🛑 Stopping system tray icon.")
        self.icon.stop()
        if self.status_thread.is_alive():
            self.status_thread.join(timeout=2)
