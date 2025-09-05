import os
import shutil
from pathlib import Path
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileSorter(FileSystemEventHandler):
    def __init__(self, download_path):
        self.download_path = Path(download_path)
        self.config_path = Path(__file__).parent / 'config.json'
        self.load_config()
        
        # Buat folder kategori jika belum ada
        self.create_folders()

    def load_config(self):
        """Memuat konfigurasi dari file config.json"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.file_categories = config.get('file_categories', {})
                print("✓ Konfigurasi berhasil dimuat dari config.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"❌ Error memuat config.json: {e}")
            print("➡️ Menggunakan konfigurasi default.")
            # Fallback ke konfigurasi default jika file tidak ada atau error
            self.file_categories = {
                'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff'],
                'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
                'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'],
                'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
                'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
                'Programs': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.appx'],
                'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go'],
                'Others': []
            }
    
    def create_folders(self):
        """Membuat folder untuk setiap kategori file"""
        for folder_name in self.file_categories.keys():
            folder_path = self.download_path / folder_name
            folder_path.mkdir(exist_ok=True)
            print(f"✓ Folder '{folder_name}' siap")
    
    def get_file_category(self, file_extension):
        """Menentukan kategori file berdasarkan ekstensi"""
        file_extension = file_extension.lower()
        
        for category, extensions in self.file_categories.items():
            if file_extension in extensions:
                return category
        
        return 'Others'  # Jika tidak ditemukan kategori
    
    def move_file(self, file_path):
        """Memindahkan file ke folder yang sesuai"""
        try:
            file_path = Path(file_path)
            
            # Skip jika itu folder atau file tersembunyi
            if file_path.is_dir() or file_path.name.startswith('.'):
                return
            
            # Skip jika file sudah ada di subfolder yang kita buat
            if file_path.parent != self.download_path:
                return
            
            # Tentukan kategori file
            file_extension = file_path.suffix
            category = self.get_file_category(file_extension)
            
            # Path tujuan
            destination_folder = self.download_path / category
            destination_path = destination_folder / file_path.name
            
            # Jika file dengan nama sama sudah ada, tambahkan nomor
            counter = 1
            original_destination = destination_path
            while destination_path.exists():
                stem = original_destination.stem
                suffix = original_destination.suffix
                destination_path = destination_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Pindahkan file
            shutil.move(str(file_path), str(destination_path))
            print(f"📁 {file_path.name} → {category}/")
            
        except Exception as e:
            print(f"❌ Error memindahkan {file_path}: {e}")
    
    def sort_existing_files(self):
        """Sorting file-file yang sudah ada di folder Downloads"""
        print("🔄 Memulai sorting file yang sudah ada...")
        
        files_moved = 0
        for file_path in self.download_path.iterdir():
            if file_path.is_file():
                self.move_file(file_path)
                files_moved += 1
        
        print(f"✅ Selesai! {files_moved} file telah dipindahkan.")
    
    def on_created(self, event):
        """Event handler ketika file baru dibuat/didownload"""
        if not event.is_directory:
            # Tunggu sebentar untuk memastikan file selesai didownload
            time.sleep(1)
            print(f"📥 File baru terdeteksi: {event.src_path}")
            self.move_file(event.src_path)
    
    def on_moved(self, event):
        """Event handler ketika file dipindahkan ke folder Downloads"""
        if not event.is_directory and Path(event.dest_path).parent == self.download_path:
            time.sleep(1)
            print(f"📥 File dipindahkan ke Downloads: {event.dest_path}")
            self.move_file(event.dest_path)

def main():
    # Path ke folder Downloads Windows 11
    downloads_path = Path.home() / "Downloads"
    
    if not downloads_path.exists():
        print("❌ Folder Downloads tidak ditemukan!")
        return
    
    print(f"🎯 Monitoring folder: {downloads_path}")
    print("=" * 50)
    
    # Inisialisasi file sorter
    file_sorter = FileSorter(downloads_path)
    
    # Sorting file yang sudah ada
    file_sorter.sort_existing_files()
    
    print("\n" + "=" * 50)
    print("👀 Memulai monitoring file baru...")
    print("Tekan Ctrl+C untuk berhenti")
    print("=" * 50)
    
    # Setup file system watcher
    observer = Observer()
    observer.schedule(file_sorter, str(downloads_path), recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Menghentikan auto-sorter...")
        observer.stop()
    
    observer.join()
    print("✅ Auto-sorter berhenti. Sampai jumpa!")

if __name__ == "__main__":
    main()
