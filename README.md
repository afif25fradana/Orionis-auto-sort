# Orionis Auto Sort

Tired of a messy Downloads folder? This application was born from the simple need to stop sorting files manually. It automatically organizes the chaos into clean, categorized folders.

## Version

v1.1.0

## Features

- **Real-time Monitoring**: Uses the `watchdog` library to monitor the Downloads folder for new files.
- **Categorization**: Sorts files into predefined categories (Images, Documents, Videos, Audio, Archives, Programs, Code, Others) based on their extension.
- **Flexible Configuration**: File categories and extensions can be easily customized by editing the `config.json` file.
- **Handles Existing Files**: Sorts all existing files in the Downloads folder when the script is first run.
- **Safe**: Ignores subdirectories and handles duplicate filenames by appending a number.
- **Security Enhanced**: Improved path validation to prevent path traversal attacks and enhanced file operation safety.
- **System Tray Integration**: Runs in the background with a system tray icon for easy access to status and controls.
- **Customizable Icon**: The application uses an `icon.png` file for the system tray icon.

## Requirements

### For Executable (Recommended)
- Windows operating system

### For Running from Source
- Python 3.x
- Required Python packages (see requirements.txt)

## Installation and Usage

### Option 1: Using the Executable (Windows)

1. **Download the latest release:**
   - Download `orionis_auto_sort.exe` from the [Releases](https://github.com/afif25fradana/Orionis-auto-sort/releases) page

2. **(Optional) Customize categories:**
   - Create a `config.json` file in the same directory as the executable if you want to customize the categories
   - If no custom config is provided, the default configuration will be used

3. **Run the application:**
   - Double-click on `orionis_auto_sort.exe`
   - The application will start running in the background with an icon in the system tray
   - Right-click on the system tray icon to see options (Status, Open Downloads Folder, Exit)

### Option 2: Running from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/afif25fradana/Orionis-auto-sort.git
   cd Orionis-auto-sort
   ```

2. **Create and activate a virtual environment:**
   
   On Windows:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS/Linux:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **(Optional) Customize categories:**
   Open the `config.json` file and modify the file extensions for each category as needed.

5. **Run the script:**
   ```bash
   python -m src.orionis.main
   ```

## How It Works

When running, Orionis Auto Sort will:

1. Create category folders in your Downloads directory if they don't exist
2. Sort any existing files in the Downloads folder
3. Monitor for new files and sort them automatically
4. Run in the background with a system tray icon for easy access
5. Enhanced security checks prevent unauthorized file access and path traversal

To exit the application, right-click on the system tray icon and select "Exit".

## Security Improvements

- **Path Traversal Prevention**: All file paths are validated to ensure they remain within the Downloads directory
- **Input Validation**: Filenames are checked for path traversal sequences to prevent unauthorized file access
- **Resource Path Validation**: Configuration and icon files are loaded with security checks to prevent access to sensitive files
- **Enhanced Error Handling**: Improved error handling prevents potential security issues from unhandled exceptions

## Building the Executable from Source

If you want to build the executable yourself:

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Build the executable:**
   ```bash
   pyinstaller --onefile --windowed --add-data "config.json;." --add-data "icon.png;." --icon="icon.png" --name "orionis_auto_sort" src/orionis/main.py
   ```

3. **Find the executable:**
   The executable will be created in the `dist` directory.
