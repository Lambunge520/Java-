import os
import runpy
import sys

# Keep these imports visible to PyInstaller. The real implementation is loaded
# dynamically from LJM_nogui.pyw and LJM.pyw.
import argparse
import base64
import concurrent.futures
import ctypes
from ctypes import wintypes
import importlib.util
import json
import logging
import platform
import re
import shlex
import shutil
import ssl
import subprocess
import tarfile
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback
from urllib.parse import urlparse
import urllib.error
import urllib.request
import webbrowser
import zipfile

if sys.platform.startswith("win"):
    import winreg


def main():
    if getattr(sys, "frozen", False):
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    runpy.run_path(os.path.join(base_dir, "LJM_nogui.pyw"), run_name="__main__")


if __name__ == "__main__":
    main()
