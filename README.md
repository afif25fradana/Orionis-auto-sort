# Orionis Auto Sort

Tired of a messy Downloads folder? This script was born from the simple need to stop sorting files manually. It automatically organizes the chaos into clean, categorized folders.

## Features

- **Real-time Monitoring**: Uses the `watchdog` library to monitor the Downloads folder for new files.
- **Categorization**: Sorts files into predefined categories (Images, Documents, Videos, Audio, Archives, Programs, Code, Others) based on their extension.
- **Flexible Configuration**: File categories and extensions can be easily customized by editing the `config.json` file.
- **Handles Existing Files**: Sorts all existing files in the Downloads folder when the script is first run.
- **Safe**: Ignores subdirectories and handles duplicate filenames by appending a number.

## Requirements

- Python 3.x

## Setup and Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/afif25fradana/Orionis-auto-sort.git
    cd auto-sort
    ```

2.  **Create and activate a virtual environment:**
    
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

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **(Optional) Customize categories:**
    Open the `config.json` file and modify the file extensions for each category as needed.

5.  **Run the script:**
    ```bash
    python orionis_auto_sort.py
    ```

The script will start monitoring your Downloads folder. Press `Ctrl+C` in the terminal to stop it.
