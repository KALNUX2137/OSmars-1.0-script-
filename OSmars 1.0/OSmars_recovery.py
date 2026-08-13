#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSmars PC - Terminal-first + PySide6 desktop (bootsys)
- Starts with GUI Selector; Recovery terminal available
- Use 'bootsys' / 'boot system' to re-enter GUI Selector
- GUI files live in boot/desktop/*.py (no auto-generation)
- from mars install → boot/instrukcja + sync (transakcje /boot)
"""
import os
import sys
import shutil
import time
import subprocess
import json
import datetime
import shlex
import signal
from pathlib import Path
import platform
from colorama import init, Fore, Style

try:
    import psutil

    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


class OSMarsPC:
    def __init__(self):
        # Root directory as Path for convenience
        self.ROOT_DIR = Path.cwd() / "OSmars PC"
        self.current_dir = self.ROOT_DIR
        self.history = []
        self.aliases = {}
        self.environment = os.environ.copy()
        self.config_file = self.ROOT_DIR / "system" / "config.json"
        self.history_file = self.ROOT_DIR / "system" / "history.txt"
        self.aliases_file = self.ROOT_DIR / "system" / "aliases.json"

        # Terminal colors (ANSI codes)
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
        }

        # PySide6 detection flag
        self.qt_available = False
        self.qt_webengine_available = False
        self._detect_pyside6()

        # internal GUI state
        self._gui_running = False
        self._fullscreen = True

        # Setup and load
        self.setup_system()
        self.load_config()
        self.load_aliases()
        self.load_history()

        # Ensure config defaults
        if 'f11_exit_enabled' not in self.config:
            self.config['f11_exit_enabled'] = True
        if 'start_gui_fullscreen' not in self.config:
            self.config['start_gui_fullscreen'] = True
        if 'show_colors' not in self.config:
            self.config['show_colors'] = True
        self.save_config(self.config)

        # Initialize console capabilities (ANSI/unicode detection)
        self.init_console()

    # ---------------- PySide6 detection ----------------
    def _detect_pyside6(self):
        try:
            import PySide6  # noqa: F401
            self.qt_available = True
            try:
                # Try importing the WebEngine
                from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
                self.qt_webengine_available = True
            except Exception:
                self.qt_webengine_available = False
        except Exception:
            self.qt_available = False
            self.qt_webengine_available = False

    # ---------------- Console init & color helpers ----------------
    def init_console(self):
        """Enable ANSI on Windows if possible and detect unicode support."""
        self.ansi = False
        try:
            if os.name == 'nt':
                import ctypes
                kernel32 = ctypes.windll.kernel32
                STD_OUTPUT_HANDLE = -11
                handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
                mode = ctypes.c_uint()
                if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                    new_mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    kernel32.SetConsoleMode(handle, new_mode)
                    self.ansi = True
            else:
                # Unix-like usually has ANSI support
                self.ansi = True
        except Exception:
            self.ansi = False

        # Unicode/box-drawing detection
        enc = (sys.stdout.encoding or "").lower()
        self.unicode_ok = ("utf" in enc) or ("65001" in enc)

        # Only use colors when enabled in config, ANSI supported and stdout is a tty
        self.use_colors = bool(self.config.get("show_colors", True)) and self.ansi and sys.stdout.isatty()

    def colorize(self, text, color):
        """Add colors only if terminal supports it."""
        if getattr(self, "use_colors", False):
            return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
        return text

        # ---------------- Setup / config / history / aliases ----------------

    def setup_system(self):
        """Create required folders and default config if missing"""
        self.ROOT_DIR.mkdir(parents=True, exist_ok=True)
        for folder in [
            "files", "boot", "system", "mods", "programs", "temp", "logs",
            # rdzeń planu OSmars
            "bin", "apps", "ver", "mars", "packages",
        ]:
            (self.ROOT_DIR / folder).mkdir(parents=True, exist_ok=True)

        # boot: desktop, updates, transakcje
        boot_desktop = self.ROOT_DIR / "boot" / "desktop"
        boot_desktop.mkdir(parents=True, exist_ok=True)
        for sub in ("updates", "pending", "snapshots", "bin"):
            (self.ROOT_DIR / "boot" / sub).mkdir(parents=True, exist_ok=True)

        # stan transakcji
        state_file = self.ROOT_DIR / "boot" / "state.json"
        if not state_file.exists():
            self._boot_write_state({
                "status": "idle",
                "last_transaction": None,
                "last_error": None,
                "updated_at": datetime.datetime.now().isoformat(),
            })

        # Desktop + images
        (self.ROOT_DIR / "files" / "Desktop").mkdir(parents=True, exist_ok=True)
        (self.ROOT_DIR / "files" / "images").mkdir(parents=True, exist_ok=True)

        programs_dir = self.ROOT_DIR / "files" / "programs"
        programs_dir.mkdir(parents=True, exist_ok=True)
        try:
            (programs_dir / "Notepad.txt").write_text("Simple Notepad (placeholder)\n", encoding='utf-8')
            (programs_dir / "Calculator.txt").write_text("Simple Calculator placeholder\n", encoding='utf-8')
            (self.ROOT_DIR / "files" / "README_GUI.txt").write_text(
                "OSmars PC GUI: Use the graphical environment to create folders, open files and launch a browser.\n",
                encoding='utf-8'
            )
        except Exception:
            pass

        # przykładowa komenda /bin/fastfetch.py
        fastfetch = self.ROOT_DIR / "bin" / "fastfetch.py"
        if not fastfetch.exists():
            fastfetch.write_text(
                '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSmars /bin/fastfetch.py — przykładowa komenda systemowa"""
import platform
import os
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    print("╔══════════════════════════════════╗")
    print("║     OSmars System Information    ║")
    print("╚══════════════════════════════════╝")
    print(f"  OS:       OSmars (userland)")
    print(f"  Host:     {platform.node()}")
    print(f"  Kernel:   {platform.system()} {platform.release()}")
    print(f"  Machine:  {platform.machine()}")
    print(f"  Python:   {platform.python_version()}")
    print(f"  Root:     {root}")
    ver_dir = root / "ver"
    if ver_dir.is_dir():
        print("  Versions:")
        for f in sorted(ver_dir.glob("*.txt")):
            try:
                print(f"    {f.stem}: {f.read_text(encoding='utf-8').strip()}")
            except Exception:
                pass

if __name__ == "__main__":
    main()
''',
                encoding="utf-8",
            )

        # /ver bazowe
        ver_osmars = self.ROOT_DIR / "ver" / "osmars.txt"
        if not ver_osmars.exists():
            ver_osmars.write_text("1.0\n", encoding="utf-8")
        ver_recovery = self.ROOT_DIR / "ver" / "recovery.txt"
        if not ver_recovery.exists():
            ver_recovery.write_text("1.0\n", encoding="utf-8")

        # default config if missing
        if not (self.ROOT_DIR / "system" / "config.json").exists():
            default_config = {
                "theme": "dark",
                "auto_save": True,
                "max_history": 100,
                "show_colors": True,
                "f11_exit_enabled": True,
                "start_gui_fullscreen": True,
                "mars_repo_url": "http://yourrepo/",
                "auto_sync_on_boot": True,
            }
            try:
                self.config = default_config
                self.save_config(default_config)
            except Exception:
                self.config = default_config

        # GUI is separate (boot/desktop/*.py) — do not generate embedded gui_system.py
        # self._generate_gui_system_file()  # disabled

    def _generate_gui_system_file(self):
        """Deprecated: GUI lives in boot/desktop/*.py. No generation."""
        return

    def create_default_wallpapers(self):
        """Create default gradient wallpapers if not exist"""
        try:
            from PIL import Image, ImageDraw

            images_dir = self.ROOT_DIR / "files" / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

            wallpapers = [
                ("osmars_blue.png", [(26, 26, 46), (22, 33, 62)]),
                ("osmars_purple.png", [(44, 20, 60), (20, 20, 40)]),
                ("osmars_green.png", [(10, 40, 30), (5, 20, 15)]),
                ("osmars_red.png", [(60, 20, 30), (30, 10, 15)])
            ]

            for filename, colors in wallpapers:
                filepath = images_dir / filename
                if not filepath.exists():
                    width, height = 1920, 1080
                    img = Image.new('RGB', (width, height))
                    draw = ImageDraw.Draw(img)

                    for y in range(height):
                        ratio = y / height
                        r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
                        g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
                        b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
                        draw.line([(0, y), (width, y)], fill=(r, g, b))

                    img.save(str(filepath))

        except ImportError:
            pass
        except Exception as e:
            print(f"Note: Could not create default wallpapers: {e}")

    def save_config(self, config):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            self.config = config
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def load_config(self):
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception:
            self.config = {
                "theme": "dark",
                "auto_save": True,
                "max_history": 100,
                "show_colors": True,
                "f11_exit_enabled": True,
                "start_gui_fullscreen": True
            }

    def load_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            self.history = lines[-self.config.get("max_history", 100):]
        except Exception:
            self.history = []

    def show_banner(self):
        """Display welcome banner (unicode and fallback) with colored system stats."""
        if getattr(self, "unicode_ok", True):
            top = '╔' + '═' * 39 + '╗'
            bottom = '╚' + '═' * 39 + '╝'
            title = "Welcome to OSmars PC v4.0"
            sub = "Terminal-first + PySide6 desktop"
            title_padding = max(0, 35 - len(title))
            sub_padding = max(0, 35 - len(sub))
            banner = f"""
    {self.colorize(top, 'cyan')}
    {self.colorize('║', 'cyan')}  {self.colorize(title, 'bold')}{' ' * title_padding}  {self.colorize('║', 'cyan')}
    {self.colorize('║', 'cyan')}  {self.colorize(sub, 'green')}{' ' * sub_padding}  {self.colorize('║', 'cyan')}
    {self.colorize(bottom, 'cyan')}

    Type {self.colorize('help', 'yellow')} to see available commands
    Type {self.colorize('exit', 'yellow')} to quit the system
    Type {self.colorize('bootsys', 'yellow')} or {self.colorize('boot system', 'yellow')} to start the GUI
            """
        else:
            banner = """
    +----------------------------------------+
    |     Welcome to OSmars PC v4.0          |
    |     Terminal-first + PySide6 desktop   |
    +----------------------------------------+

    Type help to see available commands
    Type exit to quit the system
    Type bootsys or 'boot system' to start the GUI
            """
        print(banner)

        if PSUTIL_OK:
            try:
                cpu_name = platform.processor() or "Unknown"
                if cpu_name == "": cpu_name = "Unknown"
                print(Fore.GREEN + "Procesor:", Style.BRIGHT + cpu_name)
                print(Fore.GREEN + "Architektura:", Style.BRIGHT + platform.architecture()[0])
                print(Fore.GREEN + "Rdzenie fizyczne:", Style.BRIGHT + str(psutil.cpu_count(logical=False)))
                print(Fore.GREEN + "Wątki:", Style.BRIGHT + str(psutil.cpu_count(logical=True)))

                cpu_usage = psutil.cpu_percent(interval=1)
                if cpu_usage < 50:
                    color = Fore.GREEN
                elif cpu_usage < 80:
                    color = Fore.YELLOW
                else:
                    color = Fore.RED
                print(Fore.GREEN + "Użycie CPU:", color + f"{cpu_usage} %")

                ram = psutil.virtual_memory()

                def colorize_ram(value, total):
                    percent = value / total * 100
                    if percent < 50:
                        return Fore.GREEN + str(round(value / (1024 ** 3), 2)) + " GB"
                    elif percent < 80:
                        return Fore.YELLOW + str(round(value / (1024 ** 3), 2)) + " GB"
                    else:
                        return Fore.RED + str(round(value / (1024 ** 3), 2)) + " GB"

                print(Fore.GREEN + "RAM całkowity:", Style.BRIGHT + str(round(ram.total / (1024 ** 3), 2)) + " GB")
                print(Fore.GREEN + "RAM używany:", colorize_ram(ram.used, ram.total))
                print(Fore.GREEN + "RAM wolny:", colorize_ram(ram.available, ram.total))

            except Exception as e:
                print(Fore.RED + "Nie udało się pobrać statystyk systemowych:", str(e))
        else:
            print(
                Fore.YELLOW + "Statystyki systemowe (psutil) niedostępne — zainstaluj 'psutil', żeby zobaczyć szczegóły.")

    def save_history(self):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.history[-self.config.get("max_history", 100):]))
        except Exception as e:
            print(self.colorize(f"Error saving history: {e}", 'red'))

    def add_to_history(self, command):
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            if self.config.get("auto_save", True):
                self.save_history()

    def load_aliases(self):
        try:
            if self.aliases_file.exists():
                with open(self.aliases_file, 'r', encoding='utf-8') as f:
                    self.aliases = json.load(f)
            else:
                self.aliases = {}
        except Exception:
            self.aliases = {}

    def save_aliases(self):
        try:
            self.aliases_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.aliases_file, 'w', encoding='utf-8') as f:
                json.dump(self.aliases, f, indent=2)
        except Exception as e:
            print(self.colorize(f"Error saving aliases: {e}", 'red'))

    # ---------------- pacman wrapper + downloader ----------------
    def pacman_install(self, package_name):
        """
        Install a package using pacman (Linux) or pip (cross-platform).
        Fallback: creates placeholder package file if all fails.
        """
        pkg = package_name.strip()
        if not pkg:
            print(self.colorize("No package specified.", 'yellow'))
            return

        if pkg.lower() == "pyside6":
            print(self.colorize("Installing PySide6 (Qt for Python)...", "cyan"))
            try:
                files_dir = self.ROOT_DIR / "files" / "packages"
                files_dir.mkdir(parents=True, exist_ok=True)

                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "--target", str(files_dir),
                    "PySide6", "PySide6-Addons", "PySide6-Essentials"
                ])
                print(self.colorize("✅ PySide6 installed in files/packages", "green"))
                self._detect_pyside6()
                return
            except subprocess.CalledProcessError as e:
                print(self.colorize(f"Error installing PySide6: {e}", "red"))

        pacman_ok = False
        if os.name != 'nt':
            pacman_cmd = ['sudo', 'pacman', '-S', pkg, '--noconfirm']
            print(self.colorize(f"Attempting to run: {' '.join(pacman_cmd)}", 'cyan'))
            try:
                result = subprocess.run(pacman_cmd, env=os.environ, check=False)
                if result.returncode == 0:
                    print(self.colorize(f"Package '{pkg}' installed via pacman.", 'green'))
                    pacman_ok = True
            except FileNotFoundError:
                print(self.colorize("pacman not found, will try pip instead.", 'yellow'))
            except Exception as e:
                print(self.colorize(f"Error running pacman: {e}", 'red'))

        if not pacman_ok:
            print(self.colorize(f"Installing '{pkg}' via pip...", 'cyan'))
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                print(self.colorize(f"✅ Package '{pkg}' installed via pip", 'green'))
                return
            except subprocess.CalledProcessError as e:
                print(self.colorize(f"pip install failed: {e}", 'yellow'))

        packages_dir = self.ROOT_DIR / "files" / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)
        target_file = packages_dir / f"{pkg}.pkg"
        try:
            meta = {
                "name": pkg,
                "installed_at": datetime.datetime.now().isoformat(),
                "source": "simulated",
            }
            target_file.write_text(json.dumps(meta, indent=2), encoding='utf-8')
            print(self.colorize(f"Created placeholder package file: {target_file}", 'green'))
        except Exception as e:
            print(self.colorize(f"Error creating placeholder package: {e}", 'red'))

    # ---------------- Nano-like editor ----------------
    def nano_editor(self, filepath):
        """Nano-like editor with improved cross-platform compatibility"""
        filepath = Path(filepath)
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text("", encoding='utf-8')

        try:
            content = filepath.read_text(encoding='utf-8')
        except Exception:
            content = ""

        lines = content.splitlines() if content else ['']
        cursor_line = 0
        cursor_col = 0
        scroll_offset = 0
        modified = False

        def get_terminal_size():
            try:
                return os.get_terminal_size()
            except:
                return os.terminal_size((80, 24))

        def clear_screen():
            if getattr(self, "ansi", False):
                sys.stdout.write('\033[H\033[J')
            else:
                os.system('cls' if os.name == 'nt' else 'clear')

        def draw_screen():
            ts = get_terminal_size()
            cols = ts.columns
            height = max(3, ts.lines - 4)

            clear_screen()

            header = f"OSmars Nano Editor - {filepath.name}"
            if modified:
                header += " [Modified]"
            print(self.colorize(header.center(cols), 'cyan'))
            print('-' * cols)

            visible_lines = lines[scroll_offset:scroll_offset + height]
            for i in range(height):
                if i < len(visible_lines):
                    line = visible_lines[i][:cols]
                    if i == cursor_line - scroll_offset and 0 <= cursor_line - scroll_offset < height:
                        # Kursor: cały biały blok (odwrócone kolory / białe tło)
                        if getattr(self, "use_colors", False) and getattr(self, "ansi", False):
                            inv = "\033[47;30m"  # białe tło, czarny tekst
                            rst = self.colors.get("reset", "\033[0m")
                        else:
                            inv, rst = "", ""
                        if cursor_col < len(line):
                            before = line[:cursor_col]
                            cursor_char = line[cursor_col]
                            after = line[cursor_col + 1:]
                            print(before + inv + cursor_char + rst + after)
                        else:
                            print(line + inv + " " + rst)
                    else:
                        print(line)
                else:
                    print("")

            print('-' * cols)
            help_text = "^X Exit  ^S Save  Arrows to move  (F11 exits if enabled)"
            print(self.colorize(help_text[:cols], 'green'))

            return height, cols

        def save_file():
            nonlocal modified
            try:
                filepath.write_text('\n'.join(lines), encoding='utf-8')
                modified = False
                return True
            except Exception as e:
                print(f"Error saving file: {e}")
                input("Press Enter to continue...")
                return False

        if os.name == 'nt':
            try:
                import msvcrt
                height, cols = draw_screen()

                while True:
                    if msvcrt.kbhit():
                        key = msvcrt.getch()

                        if key in (b'\x00', b'\xe0'):
                            second = msvcrt.getch()
                            second_ord = ord(second)

                            if second == b'H':
                                if cursor_line > 0:
                                    cursor_line -= 1
                                    cursor_col = min(cursor_col, len(lines[cursor_line]))
                            elif second == b'P':
                                if cursor_line < len(lines) - 1:
                                    cursor_line += 1
                                    cursor_col = min(cursor_col, len(lines[cursor_line]))
                            elif second == b'K':
                                if cursor_col > 0:
                                    cursor_col -= 1
                                elif cursor_line > 0:
                                    cursor_line -= 1
                                    cursor_col = len(lines[cursor_line])
                            elif second == b'M':
                                if cursor_col < len(lines[cursor_line]):
                                    cursor_col += 1
                                elif cursor_line < len(lines) - 1:
                                    cursor_line += 1
                                    cursor_col = 0

                            elif second_ord == 133:
                                if self.config.get('f11_exit_enabled', True):
                                    if modified:
                                        print("\nSave changes? (y/n): ", end='')
                                        choice = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                                        if choice == 'y':
                                            if save_file():
                                                break
                                        elif choice == 'n':
                                            break
                                    else:
                                        break

                            if cursor_line < scroll_offset:
                                scroll_offset = cursor_line
                            elif cursor_line >= scroll_offset + height:
                                scroll_offset = cursor_line - height + 1

                            height, cols = draw_screen()
                            continue

                        if key == b'\x18':
                            if modified:
                                print("\nSave changes? (y/n): ", end='')
                                choice = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                                if choice == 'y':
                                    if save_file():
                                        break
                                elif choice == 'n':
                                    break
                            else:
                                break

                        elif key == b'\x13':
                            save_file()
                            height, cols = draw_screen()

                        elif key == b'\r':
                            current_line = lines[cursor_line]
                            lines[cursor_line] = current_line[:cursor_col]
                            lines.insert(cursor_line + 1, current_line[cursor_col:])
                            cursor_line += 1
                            cursor_col = 0
                            modified = True

                            if cursor_line >= scroll_offset + height:
                                scroll_offset = cursor_line - height + 1

                            height, cols = draw_screen()

                        elif key == b'\x08':
                            if cursor_col > 0:
                                line = lines[cursor_line]
                                lines[cursor_line] = line[:cursor_col - 1] + line[cursor_col:]
                                cursor_col -= 1
                                modified = True
                            elif cursor_line > 0:
                                cursor_col = len(lines[cursor_line - 1])
                                lines[cursor_line - 1] += lines[cursor_line]
                                lines.pop(cursor_line)
                                cursor_line -= 1
                                modified = True

                                if cursor_line < scroll_offset:
                                    scroll_offset = cursor_line

                            height, cols = draw_screen()

                        else:
                            try:
                                ch = key.decode('utf-8', errors='ignore')
                                if ch and ch.isprintable():
                                    line = lines[cursor_line]
                                    lines[cursor_line] = line[:cursor_col] + ch + line[cursor_col:]
                                    cursor_col += 1
                                    modified = True
                                    height, cols = draw_screen()
                            except:
                                pass
                    else:
                        time.sleep(0.01)

            except (KeyboardInterrupt, ImportError):
                if 'KeyboardInterrupt' in str(sys.exc_info()[0]):
                    print("\nEditor cancelled.")
                else:
                    print("msvcrt module not available - using fallback editor")
                    self._fallback_editor(filepath, lines)
        else:
            self._fallback_editor(filepath, lines)

    def _fallback_editor(self, filepath, lines):
        """Fallback editor for systems without msvcrt"""
        try:
            print(f"\nEditing {filepath}")
            print("Simplified editor mode")
            print("Enter your content (type 'SAVE' on empty line to save and exit):")
            print("Current content:")
            for i, line in enumerate(lines):
                print(f"{i + 1:3d}: {line}")
            print("\n--- Enter new content below ---")

            new_content = []
            while True:
                try:
                    line = input("> ")
                    if line == "SAVE":
                        break
                    new_content.append(line)
                except (EOFError, KeyboardInterrupt):
                    print("\nEditor cancelled.")
                    return

            filepath.write_text('\n'.join(new_content), encoding='utf-8')
            print("File saved.")
        except Exception as e:
            print(f"Error in fallback editor: {e}")

    def _selector_read_key(self):
        """Read one key: up / down / enter / q (cross-platform)."""
        if os.name == 'nt':
            try:
                import msvcrt
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):
                    ch2 = msvcrt.getch()
                    if ch2 == b'H':
                        return 'up'
                    if ch2 == b'P':
                        return 'down'
                    return 'none'
                if ch in (b'\r', b'\n'):
                    return 'enter'
                if ch in (b'q', b'Q'):
                    return 'q'
                if ch == b'\x03':  # Ctrl+C
                    return 'q'
                return 'none'
            except Exception:
                return 'none'
        # Unix: raw terminal
        try:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A':
                            return 'up'
                        if ch3 == 'B':
                            return 'down'
                    return 'none'
                if ch in ('\r', '\n'):
                    return 'enter'
                if ch in ('q', 'Q'):
                    return 'q'
                if ch == '\x03':
                    return 'q'
                return 'none'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            # Fallback: line mode
            line = input().strip().lower()
            if line in ('q', 'quit'):
                return 'q'
            if line in ('', 'enter', 'e'):
                return 'enter'
            if line in ('w', 'up', 'k'):
                return 'up'
            if line in ('s', 'down', 'j'):
                return 'down'
            return 'none'

    def gui_selector(self):
        """Arrow-key GUI selector (GRUB-like highlight). Returns True=Recovery, False=exit."""
        desktop_dir = self.ROOT_DIR / "boot" / "desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)

        # Inverse video: white bg, black text
        INV = '\033[47;30m'
        RST = '\033[0m'
        use_inv = bool(getattr(self, 'ansi', True))

        while True:
            gui_files = sorted(
                [f for f in desktop_dir.glob("*.py") if f.is_file()],
                key=lambda p: p.name.lower()
            )

            # Build menu entries: (label, action, payload)
            # action: 'gui' | 'recovery' | 'quit'
            options = []
            for f in gui_files:
                options.append((f"  {f.name}", 'gui', f))
            if not gui_files:
                options.append(("  (brak GUI w boot/desktop/)", 'none', None))
            options.append(("  Recovery Terminal", 'recovery', None))
            options.append(("  Wyjście z OSmars", 'quit', None))

            selected = 0
            # Prefer first real GUI if present
            for i, (_, action, _) in enumerate(options):
                if action == 'gui':
                    selected = i
                    break

            def draw():
                os.system('cls' if os.name == 'nt' else 'clear')
                width = 42
                title = "OSmars GUI Selector"
                print()
                print("  ╔" + "═" * width + "╗")
                print("  ║" + title.center(width) + "║")
                print("  ╚" + "═" * width + "╝")
                print()
                print("  ↑ / ↓  wybór    Enter  zatwierdź    q  wyjście")
                print()
                for i, (label, action, _) in enumerate(options):
                    line = label.ljust(width)
                    if i == selected:
                        if use_inv:
                            print(f"  {INV}{line}{RST}")
                        else:
                            print(f"  > {label.strip()}")
                    else:
                        print(f"  {line}")
                print()

            while True:
                draw()
                key = self._selector_read_key()
                if key == 'up':
                    selected = (selected - 1) % len(options)
                elif key == 'down':
                    selected = (selected + 1) % len(options)
                elif key == 'q':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(self.colorize("Zamykanie OSmars...", 'yellow'))
                    return False
                elif key == 'enter':
                    label, action, payload = options[selected]
                    os.system('cls' if os.name == 'nt' else 'clear')
                    if action == 'quit':
                        print(self.colorize("Zamykanie OSmars...", 'yellow'))
                        return False
                    if action == 'recovery' or action == 'none':
                        print(self.colorize("→ Recovery Terminal\n", 'green'))
                        return True
                    if action == 'gui' and payload is not None:
                        print(self.colorize(f"→ Uruchamianie GUI: {payload.name}", 'green'))
                        print(self.colorize("  Recovery w tle. Zamknięcie GUI wraca do selectora.\n", 'cyan'))
                        os.system('cls' if os.name == 'nt' else 'clear')
                        self._launch_gui_file(payload)
                        break  # back to outer while → redraw selector after GUI
                # ignore other keys, redraw

    def _launch_gui_file(self, gui_path: Path):
        """Launch a selected GUI .py file from boot/desktop/. Recovery stays hidden until GUI exits."""
        # Zawsze resetuj flagę przed startem — stary True blokował GUI (fałszywe "already running")
        self._gui_running = False

        if not self.qt_available:
            print(self.colorize("PySide6 nie jest zainstalowane. Zainstaluj: sudo pacman -S pyside6", 'red'))
            return

        try:
            import importlib.util
            module_name = f"osmars_gui_{gui_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, gui_path)
            gui_module = importlib.util.module_from_spec(spec)
            # Avoid double-loading issues
            sys.modules[module_name] = gui_module
            spec.loader.exec_module(gui_module)

            if hasattr(gui_module, 'launch_gui_system'):
                # NIE ustawiaj _gui_running tu — robi to launch_gui_system.
                # Wcześniej flaga=True przed wywołaniem blokowała start GUI.
                try:
                    gui_module.launch_gui_system(self)
                finally:
                    self._gui_running = False
            elif hasattr(gui_module, 'main'):
                self._gui_running = True
                try:
                    gui_module.main()
                finally:
                    self._gui_running = False
            else:
                print(self.colorize(
                    f"Plik {gui_path.name} załadowany, ale nie znaleziono launch_gui_system() ani main().",
                    'yellow'
                ))
        except Exception as e:
            print(self.colorize(f"Błąd uruchamiania GUI ({gui_path.name}): {e}", 'red'))
            import traceback
            traceback.print_exc()
            self._gui_running = False

    def boot_system(self):
        """bootsys / boot system → pokazuje GUI Selector."""
        self.gui_selector()

    # ---------------- PySide6 helpers ----------------
    def launch_file_manager_pyside6(self, parent_window=None, start_path=None):
        """Launch file explorer - now integrated into desktop"""
        print(self.colorize("Use File Explorer from desktop or Start menu", 'yellow'))

    def _launch_marsinstall_tui(self):
        print(self.colorize("\n=== OSmars Installer (TUI) ===", "cyan"))
        print("This will install OSmars PC to a target disk.")
        print("⚠️  WARNING: This will modify your disk partitions!\n")

        # List available disks
        try:
            import subprocess
            result = subprocess.run(["lsblk", "-d", "-n", "-o", "NAME,SIZE,MODEL"],
                                    capture_output=True, text=True)
            disks = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if not disks:
                print(self.colorize("No disks found!", "red"))
                return
        except Exception as e:
            print(self.colorize(f"Error listing disks: {e}", "red"))
            return

        print("Available disks:")
        for i, disk in enumerate(disks):
            print(f"  [{i}] {disk}")

        try:
            choice = input("\nSelect disk number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return
            idx = int(choice)
            selected = disks[idx]
            device = f"/dev/{selected.split()[0]}"
            print(self.colorize(f"\nSelected: {device}", "yellow"))
        except (ValueError, IndexError):
            print(self.colorize("Invalid selection.", "red"))
            return

        confirm = input(f"\n⚠️  Install OSmars on {device}? ALL DATA WILL BE LOST! (yes/no): ").strip()
        if confirm.lower() != "yes":
            print("Installation cancelled.")
            return

        print("\nInstalling... (this may take a few minutes)")
        try:
            # 1. Format as ext4 and mount
            subprocess.run(["sudo", "mkfs.ext4", "-F", device], check=True)
            mount_point = "/mnt/osmars-install"
            subprocess.run(["sudo", "mkdir", "-p", mount_point], check=True)
            subprocess.run(["sudo", "mount", device, mount_point], check=True)

            # 2. Copy current system
            subprocess.run(["sudo", "rsync", "-aAXv", "--exclude=/boot/desktop/gui_system.py",
                            str(self.ROOT_DIR) + "/", mount_point + "/"], check=True)

            # 3. Install GRUB
            subprocess.run(
                ["sudo", "grub-install", "--target=i386-pc", "--boot-directory=" + mount_point + "/boot", device],
                check=True)
            subprocess.run(["sudo", "chroot", mount_point, "grub-mkconfig", "-o", "/boot/grub/grub.cfg"], check=True)

            # 4. (optional) Install Proton via Chaotic-AUR – skipped in TUI for now

            subprocess.run(["sudo", "umount", mount_point], check=True)
            print(self.colorize("\n✅ Installation complete! Reboot to use OSmars from disk.", "green"))
        except Exception as e:
            print(self.colorize(f"\n❌ Installation failed: {e}", "red"))

    def launch_marsinstall(self):
        """Launch the OSmars installer (terminal or GUI version)"""
        if self._gui_running:
            # Launch GUI version
            self._launch_marsinstall_gui()
        else:
            # Launch terminal (TUI) version
            self._launch_marsinstall_tui()

    def create_windows_shortcuts(self):
        """Create Windows-like shortcuts on desktop"""
        desktop = self.ROOT_DIR / "boot" / "desktop"
        try:
            desktop.mkdir(parents=True, exist_ok=True)
            shortcuts = [
                "This PC.shortcut",
                "Recycle Bin.shortcut",
                "Browser.shortcut",
                "Notepad.shortcut",
                "Calculator.shortcut",
                "Terminal.shortcut",
                "Downloads.shortcut"
            ]

            for shortcut in shortcuts:
                (desktop / shortcut).write_text(shortcut.replace(".shortcut", ""), encoding='utf-8')

            print(self.colorize("Desktop shortcuts created", 'green'))
        except Exception as e:
            print(self.colorize(f"Error creating shortcuts: {e}", 'red'))

    # ---------------- Command execution and helpers ----------------
    def execute_command(self, command):
        """Recovery: zamknięty zestaw komend (+ run/boot .py, bootsys)."""
        if not command.strip():
            return True

        try:
            parts = shlex.split(command)
        except Exception:
            parts = command.split()

        if not parts:
            return True

        self.add_to_history(command)

        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # Whitelist Recovery — rozszerzony o klasyczne komendy Linux + from mars install
        ALLOWED = {
            "help", "?", "clear", "cls", "ls", "dir", "cd", "pwd", "cat",
            "run", "boot", "bootsys", "status", "exit", "quit",
            # file ops
            "mkdir", "touch", "rm", "rmdir", "cp", "mv", "nano", "edit",
            "find", "tree", "info", "history", "alias", "config",
            # system / linux-like
            "lsblk", "df", "free", "uname", "whoami", "uptime", "ps", "top",
            "echo", "date", "hostname", "id", "env",
            # package + boot transakcje
            "from", "marsinstall", "marsuninstall", "marsupdate", "pacman",
            "sync", "rollback", "auto-sync", "autosync",
        }

        try:
            if cmd not in ALLOWED:
                print(self.colorize(
                    f"Nieznana komenda Recovery: '{cmd}'. Wpisz 'help'.",
                    'red'
                ))
                return True

            if cmd in ("bootsys",) or (cmd == "boot" and args and args[0].lower() == "system"):
                self.boot_system()
                return True

            if cmd in ("exit", "quit"):
                self.save_history()
                print(self.colorize("Zamykanie Recovery...", 'yellow'))
                return False
            elif cmd in ("help", "?"):
                self.show_help()
            elif cmd in ("ls", "dir"):
                self.list_files(args)
            elif cmd == "cd":
                self.change_directory(args)
            elif cmd == "pwd":
                rel_path = os.path.relpath(str(self.current_dir), str(self.ROOT_DIR))
                print(self.colorize(f"{rel_path}", 'cyan'))
            elif cmd == "cat":
                self.display_file(args)
            elif cmd in ("boot", "run"):
                if not args:
                    print(self.colorize("Użycie: run <plik.py>  albo  boot <plik.py>", 'yellow'))
                else:
                    self.run_python_file(args, exec_in_process=False)
            elif cmd == "status":
                self.cmd_status()
            elif cmd == "sync":
                self.boot_sync()
            elif cmd == "rollback":
                self.boot_rollback()
            elif cmd in ("clear", "cls"):
                os.system('cls' if os.name == 'nt' else 'clear')
            # --- file ops ---
            elif cmd == "mkdir":
                self.create_directory(args)
            elif cmd == "touch":
                self.create_file(args)
            elif cmd in ("rm", "del"):
                self.delete_item(args)
            elif cmd == "rmdir":
                if not args:
                    print(self.colorize("Usage: rmdir <directory>", 'yellow'))
                else:
                    path = self.current_dir / args[0]
                    try:
                        if path.is_dir() and not any(path.iterdir()):
                            path.rmdir()
                            print(self.colorize(f"Removed empty directory '{args[0]}'", 'green'))
                        else:
                            print(self.colorize(f"'{args[0]}' is not an empty directory", 'red'))
                    except Exception as e:
                        print(self.colorize(f"Error: {e}", 'red'))
            elif cmd == "cp":
                self.copy_item(args)
            elif cmd == "mv":
                self.move_item(args)
            elif cmd in ("nano", "edit"):
                self.edit_file(args)
            elif cmd == "find":
                self.find_files(args)
            elif cmd == "tree":
                self.show_tree()
            elif cmd == "info":
                self.file_info(args)
            elif cmd == "history":
                self.show_history()
            elif cmd == "alias":
                self.manage_aliases(args)
            elif cmd == "config":
                self.manage_config(args)
            # --- system / linux-like ---
            elif cmd == "lsblk":
                self.cmd_lsblk(args)
            elif cmd == "df":
                self.cmd_df(args)
            elif cmd == "free":
                self.cmd_free(args)
            elif cmd == "uname":
                self.cmd_uname(args)
            elif cmd == "whoami":
                print(os.getenv("USER") or os.getenv("USERNAME") or "unknown")
            elif cmd == "uptime":
                self.cmd_uptime()
            elif cmd in ("ps", "top"):
                self.cmd_ps(args)
            elif cmd == "echo":
                print(" ".join(args))
            elif cmd == "date":
                print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"))
            elif cmd == "hostname":
                print(platform.node() or "unknown")
            elif cmd == "id":
                print(f"uid={os.getuid() if hasattr(os, 'getuid') else 'N/A'} "
                      f"gid={os.getgid() if hasattr(os, 'getgid') else 'N/A'}")
            elif cmd == "env":
                for k, v in sorted(self.environment.items()):
                    print(f"{k}={v}")
            # --- package from mars repo ---
            elif cmd == "from":
                # from mars install|uninstall|update ...
                if len(args) >= 1 and args[0].lower() == "mars":
                    sub = args[1].lower() if len(args) > 1 else ""
                    rest = " ".join(args[2:]).strip() if len(args) > 2 else ""
                    if sub == "install":
                        self.from_mars_install(rest)
                    elif sub in ("uninstall", "remove", "rm"):
                        self.from_mars_uninstall(rest)
                    elif sub == "update":
                        self.from_mars_update(rest)
                    else:
                        print(self.colorize(
                            "Użycie:\n"
                            "  from mars install <nazwa>\n"
                            "  from mars uninstall <nazwa>\n"
                            "  from mars update [nazwa]",
                            "yellow",
                        ))
                else:
                    print(self.colorize("Użycie: from mars install|uninstall|update ...", "yellow"))
            elif cmd == "marsinstall":
                self.from_mars_install(" ".join(args).strip())
            elif cmd == "marsuninstall":
                self.from_mars_uninstall(" ".join(args).strip())
            elif cmd == "marsupdate":
                self.from_mars_update(" ".join(args).strip())
            elif cmd in ("auto-sync", "autosync"):
                self.cmd_auto_sync(args)
            elif cmd == "pacman":
                if args and args[0] in ("-S", "--sync") and len(args) > 1:
                    self.pacman_install(args[1])
                else:
                    print(self.colorize("Użycie: pacman -S <package>   lub   from mars install <package>", 'yellow'))
            return True
        except Exception as e:
            print(self.colorize(f"Błąd: {e}", 'red'))
            return True

    def run_python_file(self, args, exec_in_process=False):
        if not args:
            print(self.colorize("Usage: run <python_file>   or   run --exec <python_file>", 'yellow'))
            return

        filename = args[0] if args[0].endswith('.py') else args[0] + '.py'
        path = Path(self.current_dir) / filename

        if not path.exists():
            print(self.colorize(f"File '{filename}' not found", 'red'))
            return

        print(self.colorize(f"\n--- Executing {filename} ---", 'cyan'))
        old_cwd = Path.cwd()
        try:
            if not exec_in_process:
                result = subprocess.run([sys.executable, str(path)], cwd=str(self.current_dir), env=self.environment)
                if result.returncode != 0:
                    print(self.colorize(f"Process exited with code {result.returncode}", 'red'))
            else:
                code = path.read_text(encoding='utf-8')
                namespace = {
                    '__name__': '__main__',
                    '__file__': str(path),
                    'osmars_pc': self
                }
                exec(compile(code, str(path), 'exec'), namespace)
            print(self.colorize(f"--- Execution completed ---\n", 'cyan'))
        except Exception as e:
            print(self.colorize(f"Execution error: {e}", 'red'))
        finally:
            try:
                os.chdir(old_cwd)
            except Exception:
                pass

    # ---------------- File/dir commands ----------------
    def list_files(self, args):
        show_details = '-l' in args
        show_hidden = '-a' in args
        try:
            items = sorted(os.listdir(str(self.current_dir)))
            if not show_hidden:
                items = [item for item in items if not item.startswith('.')]

            if show_details:
                print(f"{'Name':<30} {'Size':<10} {'Modified':<20} {'Type':<10}")
                print("-" * 80)
                for item in items:
                    path = self.current_dir / item
                    try:
                        stat = path.stat()
                        size = stat.st_size if path.is_file() else 0
                        modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        item_type = "DIR" if path.is_dir() else "FILE"
                        color = 'blue' if path.is_dir() else 'white'
                        colored_name = self.colorize(item, color)
                        display_len = len(item)
                        padding = max(0, 30 - display_len)
                        print(f"{colored_name}{' ' * padding} {size:<10} {modified:<20} {item_type:<10}")
                    except Exception:
                        colored_name = self.colorize(item, 'red')
                        display_len = len(item)
                        padding = max(0, 30 - display_len)
                        print(f"{colored_name}{' ' * padding} {'?':<10} {'?':<20} {'?':<10}")
            else:
                for item in items:
                    path = self.current_dir / item
                    color = 'blue' if path.is_dir() else 'white'
                    print(self.colorize(item, color))
        except PermissionError:
            print(self.colorize("Permission denied", 'red'))
        except Exception as e:
            print(self.colorize(f"Error listing files: {e}", 'red'))

    def change_directory(self, args):
        if not args:
            target = self.ROOT_DIR
        elif args[0] == "..":
            parent_dir = self.current_dir.parent
            try:
                if str(parent_dir) == str(self.ROOT_DIR.parent):
                    print(self.colorize("Cannot go outside OSmars PC directory!", 'red'))
                    return
                elif parent_dir >= self.ROOT_DIR:
                    target = parent_dir
                else:
                    print(self.colorize("Cannot go outside OSmars PC directory!", 'red'))
                    return
            except Exception:
                print(self.colorize("Cannot go up from here", 'red'))
                return
        else:
            target = (self.current_dir / args[0]).resolve()

        try:
            if target.is_dir() and target >= self.ROOT_DIR:
                self.current_dir = target
            else:
                print(self.colorize(f"Directory '{args[0]}' not found or access denied", 'red'))
        except Exception:
            print(self.colorize(f"Directory '{args[0]}' not found or access denied", 'red'))

    def create_directory(self, args):
        if not args:
            print(self.colorize("Usage: mkdir <directory_name>", 'yellow'))
            return
        name = args[0] if args and args[0] else None
        if not name:
            print(self.colorize("No folder name provided.", 'yellow'))
            return
        path = self.current_dir / name
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(self.colorize(f"Directory '{name}' created", 'green'))
        except Exception as e:
            print(self.colorize(f"Error creating directory: {e}", 'red'))

    def create_file(self, args):
        if not args:
            print(self.colorize("Usage: touch <filename>", 'yellow'))
            return
        path = self.current_dir / args[0]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
            print(self.colorize(f"File '{args[0]}' created", 'green'))
        except Exception as e:
            print(self.colorize(f"Error creating file: {e}", 'red'))

    def create_python_file(self, args):
        if not args:
            print(self.colorize("Usage: ctpy <filename>", 'yellow'))
            return
        filename = args[0] if args[0].endswith('.py') else args[0] + '.py'
        path = self.current_dir / filename
        template = '''#!/usr/bin/env python3
"""
OSmars PC Python File
Created: {}
"""

def main():
    print("Hello from OSmars PC!")

if __name__ == "__main__":
    main()
'''.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(template, encoding='utf-8')
            print(self.colorize(f"Python file '{filename}' created", 'green'))
        except Exception as e:
            print(self.colorize(f"Error creating python file: {e}", 'red'))

    def delete_item(self, args):
        if not args:
            print(self.colorize("Usage: rm <filename>", 'yellow'))
            return
        path = self.current_dir / args[0]
        if not path.exists():
            print(self.colorize(f"'{args[0]}' not found", 'red'))
            return
        try:
            if path.is_dir():
                print(f"Delete directory '{args[0]}' and all contents? (y/N): ", end='')
                response = input().strip()
                if response.lower().startswith('y'):
                    shutil.rmtree(str(path))
                    print(self.colorize(f"Directory '{args[0]}' deleted", 'green'))
            else:
                path.unlink()
                print(self.colorize(f"File '{args[0]}' deleted", 'green'))
        except Exception as e:
            print(self.colorize(f"Error deleting: {e}", 'red'))

    def copy_item(self, args):
        if len(args) < 2:
            print(self.colorize("Usage: cp <source> <destination>", 'yellow'))
            return
        src = self.current_dir / args[0]
        dst = self.current_dir / args[1]

        if not src.exists():
            print(self.colorize(f"Source '{args[0]}' not found", 'red'))
            return

        try:
            if src.is_dir():
                if dst.exists():
                    print(self.colorize(f"Destination '{args[1]}' already exists", 'red'))
                    return
                shutil.copytree(str(src), str(dst))
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
            print(self.colorize(f"Copied '{args[0]}' to '{args[1]}'", 'green'))
        except Exception as e:
            print(self.colorize(f"Error copying: {e}", 'red'))

    def move_item(self, args):
        if len(args) < 2:
            print(self.colorize("Usage: mv <source> <destination>", 'yellow'))
            return
        src = self.current_dir / args[0]
        dst = self.current_dir / args[1]

        if not src.exists():
            print(self.colorize(f"Source '{args[0]}' not found", 'red'))
            return

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            print(self.colorize(f"Moved '{args[0]}' to '{args[1]}'", 'green'))
        except Exception as e:
            print(self.colorize(f"Error moving: {e}", 'red'))

    def display_file(self, args):
        if not args:
            print(self.colorize("Usage: cat <filename>", 'yellow'))
            return
        path = self.current_dir / args[0]

        if not path.exists():
            print(self.colorize(f"File '{args[0]}' not found", 'red'))
            return

        try:
            content = path.read_text(encoding='utf-8')
            print(content)
        except UnicodeDecodeError:
            print(self.colorize("File contains binary data or unsupported encoding", 'red'))
        except Exception as e:
            print(self.colorize(f"Error reading file: {e}", 'red'))

    def edit_file(self, args):
        if not args:
            print(self.colorize("Usage: edit <filename>", 'yellow'))
            return
        path = self.current_dir / args[0]
        self.nano_editor(path)

    def find_files(self, args):
        if not args:
            print(self.colorize("Usage: find <pattern>", 'yellow'))
            return
        pattern = args[0]
        matches = self.search_files(pattern, self.current_dir)
        if matches:
            print(self.colorize(f"Found {len(matches)} matches:", 'green'))
            for match in matches:
                try:
                    rel_path = os.path.relpath(match, str(self.current_dir))
                    print(f"  {rel_path}")
                except Exception:
                    print(f"  {match}")
        else:
            print(self.colorize("No files found", 'yellow'))

    def file_info(self, args):
        if not args:
            print(self.colorize("Usage: info <filename>", 'yellow'))
            return
        path = self.current_dir / args[0]
        info = self.get_file_info(path)
        if info:
            print(f"File: {args[0]}")
            print(f"Size: {info['size']} bytes")
            print(f"Modified: {info['modified']}")
            print(f"Readable: {info['readable']}")
            print(f"Writable: {info['writable']}")
            print(f"Executable: {info['executable']}")
        else:
            print(self.colorize(f"Cannot get info for '{args[0]}' (file may not exist)", 'red'))

    def show_history(self):
        if not self.history:
            print(self.colorize("No command history", 'yellow'))
            return
        print(self.colorize("Command History:", 'cyan'))
        for i, cmd in enumerate(self.history[-20:], 1):
            print(f"{i:2d}: {cmd}")

    def manage_aliases(self, args):
        if not args:
            if self.aliases:
                print(self.colorize("Current aliases:", 'cyan'))
                for alias, command in self.aliases.items():
                    print(f"  {alias} = {command}")
            else:
                print(self.colorize("No aliases defined", 'yellow'))
            return

        alias_def = ' '.join(args)
        if alias_def.startswith("-d "):
            name = alias_def[3:].strip()
            if name in self.aliases:
                del self.aliases[name]
                self.save_aliases()
                print(self.colorize(f"Alias '{name}' removed", 'green'))
            else:
                print(self.colorize(f"Alias '{name}' not found", 'yellow'))
            return

        if '=' in alias_def:
            alias, command = alias_def.split('=', 1)
            alias = alias.strip()
            command = command.strip()
            if alias and command:
                self.aliases[alias] = command
                self.save_aliases()
                print(self.colorize(f"Alias '{alias}' created", 'green'))
            else:
                print(self.colorize("Invalid alias format", 'red'))
        else:
            print(self.colorize("Usage: alias <n>=<command>   or   alias -d <n>", 'yellow'))

    def manage_config(self, args):
        if len(args) == 0:
            print(self.colorize("Current configuration:", 'cyan'))
            for key, value in self.config.items():
                print(f"  {key}: {value}")
        elif len(args) == 1:
            key = args[0]
            if key in self.config:
                print(f"{key}: {self.config[key]}")
            else:
                print(self.colorize(f"Configuration key '{key}' not found", 'red'))
        elif len(args) == 2:
            key, value = args
            if value.lower() in ['true', 'false']:
                value_parsed = value.lower() == 'true'
            elif value.isdigit():
                value_parsed = int(value)
            else:
                value_parsed = value
            self.config[key] = value_parsed
            self.save_config(self.config)
            print(self.colorize(f"Configuration updated: {key} = {value_parsed}", 'green'))
        else:
            print(self.colorize("Usage: config [key] [value]", 'yellow'))

    def show_tree(self, directory=None, prefix="", max_depth=3, current_depth=0):
        if directory is None:
            directory = self.current_dir
            print(self.colorize(f"Directory tree for: {directory.name}", 'cyan'))

        if current_depth > max_depth:
            return

        try:
            items = sorted(os.listdir(str(directory)))
            dirs = [item for item in items if (directory / item).is_dir()]
            files = [item for item in items if (directory / item).is_file()]

            for i, dir_name in enumerate(dirs):
                is_last_dir = (i == len(dirs) - 1) and len(files) == 0
                tree_char = "└── " if is_last_dir else "├── "
                print(f"{prefix}{tree_char}{self.colorize(dir_name, 'blue')}")

                new_prefix = prefix + ("    " if is_last_dir else "│   ")
                try:
                    self.show_tree(directory / dir_name, new_prefix, max_depth, current_depth + 1)
                except PermissionError:
                    print(f"{new_prefix}[Permission Denied]")
                except Exception:
                    print(f"{new_prefix}[Error accessing directory]")

            for i, file_name in enumerate(files):
                is_last = i == len(files) - 1
                tree_char = "└── " if is_last else "├── "
                print(f"{prefix}{tree_char}{file_name}")

        except PermissionError:
            print(f"{prefix}[Permission Denied]")
        except Exception as e:
            print(f"{prefix}[Error: {e}]")

    def get_prompt(self):
        try:
            rel_path = os.path.relpath(str(self.current_dir), str(self.ROOT_DIR))
            if rel_path == '.':
                rel_path = '~'
            time_str = datetime.datetime.now().strftime('%H:%M')
            # Recovery prompt: <recovery>:~[HH:MM]$
            prompt = f"{self.colorize('<recovery>', 'cyan')}:{self.colorize(rel_path, 'blue')}"
            prompt += f"{self.colorize('[' + time_str + ']', 'yellow')}$ "
            return prompt
        except Exception:
            return "<recovery>:~$ "

    def show_help(self):
        help_text = """
OSmars Recovery — dostępne komendy:

  help, ?              - ta pomoc
  clear, cls           - wyczyść ekran
  ls, dir [-l] [-a]    - lista plików
  cd <dir>             - zmiana katalogu
  pwd                  - bieżący katalog
  cat <file>           - pokaż plik
  mkdir <dir>          - utwórz katalog
  touch <file>         - utwórz plik
  rm <file>            - usuń plik/katalog
  rmdir <dir>          - usuń pusty katalog
  cp <src> <dst>       - kopiuj
  mv <src> <dst>       - przenieś
  nano / edit <file>   - edytor (nano-like)
  find <pattern>       - szukaj plików
  tree                 - drzewo katalogów
  info <file>          - informacje o pliku
  history              - historia komend
  alias [name=cmd]     - aliasy
  config [key] [val]   - konfiguracja

  lsblk                - lista dysków/bloków
  df                   - miejsce na dysku
  free                 - pamięć RAM
  uname [-a]           - info o systemie
  whoami / id / hostname / date / uptime / env / echo / ps

  run / boot <file.py> - uruchom skrypt Python
  bootsys / boot system- GUI Selector
  status               - status Recovery + boot/transakcje
  exit, quit           - wyjście

  from mars install <pkg>     - pobierz z repo (mars/system/bin)
  from mars uninstall <pkg>   - usuń paczkę (apps/bin/ver)
  from mars update [pkg]      - sprawdź wersje i zaktualizuj
  marsinstall / marsuninstall / marsupdate
  sync                        - zastosuj boot/instrukcja
  rollback                    - przywróć snapshot
  auto-sync [on|off|status]   - auto sync po pobraniu
  pacman -S <pkg>             - lokalny install

Boot:
  install → Downloads + instrukcja → sync (jeśli auto-sync on)
  update  → porównuje ver/*.json z API serwera

Repo: config mars_repo_url
"""
        print(self.colorize(help_text, 'green'))

    # ---------------- Linux-like helpers + Mars repo ----------------
    def cmd_lsblk(self, args=None):
        """Simple lsblk-like listing of block devices."""
        try:
            if os.name != 'nt':
                result = subprocess.run(
                    ["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    print(result.stdout)
                    return
        except Exception:
            pass
        # Fallback pure-Python-ish
        print(f"{'NAME':<12} {'SIZE':<10} {'TYPE':<8} {'MOUNTPOINT'}")
        print("-" * 50)
        try:
            if PSUTIL_OK:
                for part in psutil.disk_partitions(all=False):
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        size = f"{usage.total / (1024**3):.1f}G"
                    except Exception:
                        size = "?"
                    print(f"{part.device.split('/')[-1]:<12} {size:<10} {'part':<8} {part.mountpoint}")
            else:
                # minimal
                print(f"{'sda':<12} {'?':<10} {'disk':<8} /")
        except Exception as e:
            print(self.colorize(f"lsblk error: {e}", 'red'))

    def cmd_df(self, args=None):
        try:
            if os.name != 'nt':
                result = subprocess.run(["df", "-h"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(result.stdout)
                    return
        except Exception:
            pass
        if PSUTIL_OK:
            print(f"{'Filesystem':<20} {'Size':>8} {'Used':>8} {'Avail':>8} {'Use%':>6} Mounted on")
            for part in psutil.disk_partitions(all=False):
                try:
                    u = psutil.disk_usage(part.mountpoint)
                    print(f"{part.device:<20} {u.total/(1024**3):>7.1f}G {u.used/(1024**3):>7.1f}G "
                          f"{u.free/(1024**3):>7.1f}G {u.percent:>5.0f}% {part.mountpoint}")
                except Exception:
                    pass
        else:
            total, used, free = shutil.disk_usage(str(self.ROOT_DIR))
            print(f"Total: {total/(1024**3):.1f}G  Used: {used/(1024**3):.1f}G  Free: {free/(1024**3):.1f}G")

    def cmd_free(self, args=None):
        if PSUTIL_OK:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            print(f"{'':>8} {'total':>10} {'used':>10} {'free':>10} {'available':>10}")
            print(f"{'Mem:':>8} {mem.total/(1024**2):>9.0f}M {mem.used/(1024**2):>9.0f}M "
                  f"{mem.available/(1024**2):>9.0f}M {mem.available/(1024**2):>9.0f}M")
            print(f"{'Swap:':>8} {swap.total/(1024**2):>9.0f}M {swap.used/(1024**2):>9.0f}M "
                  f"{swap.free/(1024**2):>9.0f}M")
        else:
            print(self.colorize("psutil niedostępne — zainstaluj psutil", 'yellow'))

    def cmd_uname(self, args=None):
        if args and '-a' in args:
            print(f"{platform.system()} {platform.node()} {platform.release()} "
                  f"{platform.version()} {platform.machine()} {platform.processor()}")
        else:
            print(platform.system())

    def cmd_uptime(self):
        if PSUTIL_OK:
            boot = datetime.datetime.fromtimestamp(psutil.boot_time())
            up = datetime.datetime.now() - boot
            days = up.days
            hours, rem = divmod(up.seconds, 3600)
            mins, _ = divmod(rem, 60)
            print(f"up {days} days, {hours}:{mins:02d}")
        else:
            print("uptime: (psutil required)")

    def cmd_ps(self, args=None):
        if PSUTIL_OK:
            print(f"{'PID':>6} {'NAME':<25} {'CPU%':>6} {'MEM%':>6}")
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    print(f"{info['pid']:>6} {str(info['name'])[:25]:<25} "
                          f"{info['cpu_percent'] or 0:>5.1f}% {info['memory_percent'] or 0:>5.1f}%")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        else:
            print(self.colorize("psutil niedostępne", 'yellow'))

    # ==================== BOOT TRANSACTIONS ====================
    def _boot_state_path(self) -> Path:
        return self.ROOT_DIR / "boot" / "state.json"

    def _boot_instrukcja_path(self) -> Path:
        return self.ROOT_DIR / "boot" / "instrukcja.json"

    def _boot_instrukcja_py_path(self) -> Path:
        return self.ROOT_DIR / "boot" / "instrukcja.py"

    def _boot_write_state(self, state: dict):
        path = self._boot_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        state = dict(state)
        state["updated_at"] = datetime.datetime.now().isoformat()
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _boot_read_state(self) -> dict:
        path = self._boot_state_path()
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"status": "idle", "last_transaction": None, "last_error": None}

    def _boot_read_instrukcja(self) -> dict | None:
        path = self._boot_instrukcja_path()
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(self.colorize(f"[ERR] Nie można odczytać instrukcja.json: {e}", "red"))
            return None

    def _boot_has_pending(self) -> bool:
        state = self._boot_read_state()
        if state.get("status") in ("pending", "failed"):
            return True
        if self._boot_instrukcja_path().exists():
            return True
        if self._boot_instrukcja_py_path().exists():
            return True
        return False

    def cmd_status(self):
        print(self.colorize("OSmars Recovery", "cyan"))
        print(f"  ROOT: {self.ROOT_DIR}")
        print(f"  CWD:  {self.current_dir}")
        print(f"  Qt:   {'OK' if self.qt_available else 'brak'}")
        desk = self.ROOT_DIR / "boot" / "desktop"
        guis = list(desk.glob("*.py")) if desk.exists() else []
        print(f"  GUI:  {', '.join(p.name for p in guis) or '(brak)'}")
        state = self._boot_read_state()
        st = state.get("status", "idle")
        color = "green" if st == "idle" else ("yellow" if st == "pending" else "red")
        print(self.colorize(f"  Boot: {st}", color))
        if state.get("last_transaction"):
            print(f"  Last: {state.get('last_transaction')}")
        if state.get("last_error"):
            print(self.colorize(f"  Error: {state.get('last_error')}", "red"))
        instr = self._boot_read_instrukcja()
        if instr:
            print(f"  Instrukcja: {instr.get('id', '?')} action={instr.get('action')} pkg={instr.get('package')}")
        elif self._boot_instrukcja_py_path().exists():
            print("  Instrukcja: boot/instrukcja.py (skrypt)")
        ver = self.ROOT_DIR / "ver"
        if ver.is_dir():
            parts = []
            for f in sorted(ver.glob("*.txt")):
                try:
                    parts.append(f"{f.stem}={f.read_text(encoding='utf-8').strip()}")
                except Exception:
                    pass
            if parts:
                print(f"  Ver:  {', '.join(parts)}")

    def boot_check_on_startup(self):
        """
        Przy starcie Recovery/Selector: sprawdź /boot i ewentualnie zastosuj transakcję.
        Plan: Kernel → Recovery → instrukcja → apply → verify → GUI
        """
        if not self._boot_has_pending():
            return
        state = self._boot_read_state()
        print(self.colorize("\n═══ Boot: oczekująca transakcja ═══", "yellow"))
        instr = self._boot_read_instrukcja()
        if instr:
            print(f"  id:     {instr.get('id')}")
            print(f"  action: {instr.get('action')}")
            print(f"  package:{instr.get('package')}")
        elif self._boot_instrukcja_py_path().exists():
            print("  skrypt: boot/instrukcja.py")
        print(f"  status: {state.get('status')}")

        auto = bool(self.config.get("auto_sync_on_boot", True))
        if auto:
            print(self.colorize("  → auto_sync_on_boot=True — uruchamiam sync…", "cyan"))
            ok = self.boot_sync()
            if not ok:
                print(self.colorize(
                    "  [ERR] Transakcja nieudana — system w poprzednim stanie (rollback).\n"
                    "  GUI może się uruchomić, ale napraw: status / rollback / sync",
                    "red",
                ))
        else:
            print(self.colorize("  Uruchom:  sync   aby zastosować zmiany", "cyan"))
            print(self.colorize("  Anuluj:   rollback", "cyan"))

    def _boot_snapshot(self, paths: list) -> Path:
        """Zapisz kopie ścieżek (względem ROOT) do boot/snapshots/<ts>/"""
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snap = self.ROOT_DIR / "boot" / "snapshots" / ts
        snap.mkdir(parents=True, exist_ok=True)
        meta = {"paths": [], "created": ts}
        for rel in paths:
            rel = str(rel).replace(chr(92), "/").lstrip("/")
            if rel.startswith("@host/"):
                src = self.ROOT_DIR.parent / rel[len("@host/"):]
                safe = rel[len("@host/"):].replace("/", "__")
                dst = snap / ("_host_" + safe)
            else:
                src = self.ROOT_DIR / rel
                dst = snap / rel
            try:
                if src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    meta["paths"].append({"rel": rel, "type": "file", "existed": True})
                elif src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    meta["paths"].append({"rel": rel, "type": "dir", "existed": True})
                else:
                    meta["paths"].append({"rel": rel, "type": "missing", "existed": False})
            except Exception as e:
                meta["paths"].append({"rel": rel, "type": "error", "error": str(e)})
        (snap / "snapshot.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return snap

    def _boot_restore_snapshot(self, snap: Path) -> bool:
        meta_path = snap / "snapshot.json"
        if not meta_path.exists():
            print(self.colorize("[ERR] Brak snapshot.json", "red"))
            return False
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(self.colorize(f"[ERR] snapshot: {e}", "red"))
            return False
        for item in meta.get("paths", []):
            rel = item.get("rel", "")
            target = self.ROOT_DIR / rel
            backup = snap / rel
            try:
                if not item.get("existed"):
                    # wcześniej nie istniało — usuń jeśli powstało
                    if target.is_file():
                        target.unlink()
                    elif target.is_dir():
                        shutil.rmtree(target)
                elif item.get("type") == "file" and backup.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, target)
                elif item.get("type") == "dir" and backup.is_dir():
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(backup, target)
            except Exception as e:
                print(self.colorize(f"[ERR] rollback {rel}: {e}", "red"))
                return False
        return True

    def _boot_apply_step(self, step: dict) -> None:
        op = (step.get("op") or "").lower()
        root = self.ROOT_DIR

        if op == "mkdir":
            path = root / step["path"]
            path.mkdir(parents=True, exist_ok=True)

        elif op == "copy":
            src = root / step["src"]
            dst_rel = step["dst"]
            # @host/ = katalog nadrzędny względem OSmars PC (np. OSmars_recovery.py)
            if isinstance(dst_rel, str) and dst_rel.startswith("@host/"):
                dst = root.parent / dst_rel[len("@host/"):]
            else:
                dst = root / dst_rel
            if not src.exists():
                raise FileNotFoundError(f"copy: brak źródła {step['src']}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        elif op == "move":
            src = root / step["src"]
            dst = root / step["dst"]
            if not src.exists():
                raise FileNotFoundError(f"move: brak {step['src']}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(src), str(dst))

        elif op == "remove":
            path = root / step["path"]
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

        elif op == "write_ver":
            comp = step.get("component") or step.get("name")
            ver = step.get("version", "1.0")
            if not comp:
                raise ValueError("write_ver: brak component")
            vdir = root / "ver"
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / f"{comp}.txt").write_text(str(ver).strip() + "\n", encoding="utf-8")
            jdata = {
                "id": comp,
                "name": step.get("display_name") or comp,
                "version": str(ver).strip(),
                "type": step.get("pkg_type") or "app",
                "files": step.get("files") or [],
                "updated_at": datetime.datetime.now().isoformat(),
            }
            (vdir / f"{comp}.json").write_text(
                json.dumps(jdata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )

        elif op == "write_text":
            path = root / step["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(step.get("content", ""), encoding="utf-8")

        elif op == "extract_mars":
            import zipfile
            src = root / step["src"]
            dst = root / step["dst"]
            if not src.is_file():
                raise FileNotFoundError(f"extract_mars: brak {step['src']}")
            if dst.exists():
                shutil.rmtree(dst)
            dst.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(dst)

        elif op == "run_py":
            # uruchom skrypt w kontekście ROOT (bez interakcji)
            script = root / step["path"]
            if not script.is_file():
                raise FileNotFoundError(f"run_py: brak {step['path']}")
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=int(step.get("timeout", 60)),
            )
            if result.returncode != 0:
                raise RuntimeError(f"run_py exit {result.returncode}: {result.stderr[:500]}")

        else:
            raise ValueError(f"Nieznana operacja w instrukcji: {op}")

    def _boot_verify_step(self, step: dict) -> None:
        op = (step.get("op") or "").lower()
        root = self.ROOT_DIR
        if op == "exists":
            pref = step["path"]
            if isinstance(pref, str) and pref.startswith("@host/"):
                path = root.parent / pref[len("@host/"):]
            else:
                path = root / pref
            if not path.exists():
                raise FileNotFoundError(f"verify exists: brak {step['path']}")
        elif op == "not_exists":
            path = root / step["path"]
            if path.exists():
                raise FileExistsError(f"verify not_exists: nadal jest {step['path']}")
        elif op == "contains":
            path = root / step["path"]
            text = path.read_text(encoding="utf-8")
            if step.get("text", "") not in text:
                raise ValueError(f"verify contains: brak tekstu w {step['path']}")
        else:
            raise ValueError(f"Nieznana weryfikacja: {op}")

    def _boot_apply_instrukcja_json(self, instr: dict) -> None:
        steps = instr.get("steps") or []
        print(self.colorize(f"  Apply: {len(steps)} krok(ów)…", "cyan"))
        for i, step in enumerate(steps, 1):
            op = step.get("op", "?")
            print(f"    [{i}/{len(steps)}] {op} {step.get('path') or step.get('dst') or step.get('src') or ''}")
            self._boot_apply_step(step)

    def _boot_verify_instrukcja_json(self, instr: dict) -> None:
        checks = instr.get("verify") or []
        if not checks:
            print(self.colorize("  Verify: (brak reguł — pomijam)", "yellow"))
            return
        print(self.colorize(f"  Verify: {len(checks)} reguł…", "cyan"))
        for i, step in enumerate(checks, 1):
            print(f"    [{i}/{len(checks)}] {step.get('op')} {step.get('path', '')}")
            self._boot_verify_step(step)

    def _boot_apply_instrukcja_py(self) -> None:
        """Uruchom boot/instrukcja.py z funkcjami apply/verify/rollback."""
        path = self._boot_instrukcja_py_path()
        import importlib.util
        spec = importlib.util.spec_from_file_location("osmars_instrukcja", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ctx = {
            "root": self.ROOT_DIR,
            "bin": self.ROOT_DIR / "bin",
            "apps": self.ROOT_DIR / "apps",
            "boot": self.ROOT_DIR / "boot",
            "ver": self.ROOT_DIR / "ver",
        }
        if hasattr(mod, "apply"):
            print(self.colorize("  Apply: instrukcja.py → apply()", "cyan"))
            mod.apply(ctx)
        else:
            raise RuntimeError("instrukcja.py bez funkcji apply(ctx)")
        if hasattr(mod, "verify"):
            print(self.colorize("  Verify: instrukcja.py → verify()", "cyan"))
            ok = mod.verify(ctx)
            if ok is False:
                raise RuntimeError("instrukcja.py verify() zwróciło False")

    def boot_sync(self) -> bool:
        """
        sync — odczytaj /boot/instrukcja, zastosuj, zweryfikuj; przy błędzie rollback.
        Zwraca True przy sukcesie.
        """
        print(self.colorize("\n═══ OSmars sync (boot transaction) ═══", "cyan"))
        instr = self._boot_read_instrukcja()
        has_py = self._boot_instrukcja_py_path().exists()

        if not instr and not has_py:
            print(self.colorize("Brak oczekującej instrukcji w /boot.", "yellow"))
            self._boot_write_state({"status": "idle", "last_transaction": None, "last_error": None})
            return True

        txn_id = (instr or {}).get("id") or "instrukcja.py"
        rollback_paths = list((instr or {}).get("rollback_paths") or [])
        # domyślne ścieżki do snapshota
        if instr:
            for step in instr.get("steps") or []:
                for key in ("dst", "path"):
                    if step.get(key):
                        rollback_paths.append(step[key])
            if instr.get("package"):
                rollback_paths.append(f"apps/{instr['package']}")
        rollback_paths = list(dict.fromkeys(rollback_paths))  # unique

        self._boot_write_state({
            "status": "applying",
            "last_transaction": txn_id,
            "last_error": None,
        })

        snap = None
        try:
            if rollback_paths:
                print(self.colorize(f"  Snapshot: {len(rollback_paths)} ścieżek…", "cyan"))
                snap = self._boot_snapshot(rollback_paths)
                # zapisz ścieżkę snapshota do state
                st = self._boot_read_state()
                st["snapshot"] = str(snap.relative_to(self.ROOT_DIR))
                self._boot_write_state(st)

            if instr:
                self._boot_apply_instrukcja_json(instr)
                self._boot_verify_instrukcja_json(instr)
            if has_py:
                self._boot_apply_instrukcja_py()

            # sukces — posprzątaj instrukcję
            if self._boot_instrukcja_path().exists():
                self._boot_instrukcja_path().unlink()
            if has_py:
                # przenieś wykonany skrypt do archiwum
                done = self.ROOT_DIR / "boot" / "snapshots" / f"instrukcja_done_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                try:
                    shutil.move(str(self._boot_instrukcja_py_path()), str(done))
                except Exception:
                    self._boot_instrukcja_py_path().unlink(missing_ok=True)

            # wyczyść pending dla tej paczki
            pending = self.ROOT_DIR / "boot" / "pending"
            if instr and instr.get("package"):
                pkg_pending = pending / instr["package"]
                if pkg_pending.exists():
                    shutil.rmtree(pkg_pending, ignore_errors=True)

            self._boot_write_state({
                "status": "idle",
                "last_transaction": txn_id,
                "last_error": None,
                "snapshot": str(snap.relative_to(self.ROOT_DIR)) if snap else None,
            })
            print(self.colorize(f"\n✅ Transakcja '{txn_id}' zastosowana i zweryfikowana.", "green"))
            return True

        except Exception as e:
            err = str(e)
            print(self.colorize(f"\n[ERR] {err}", "red"))
            print(self.colorize("Installation integrity failure.", "red"))
            print(self.colorize("Status: ABORTED — rollback…", "yellow"))
            if snap and snap.exists():
                if self._boot_restore_snapshot(snap):
                    print(self.colorize("  Rollback OK — poprzedni stan przywrócony.", "green"))
                else:
                    print(self.colorize("  Rollback CZĘŚCIOWY / BŁĄD — sprawdź ręcznie.", "red"))
            self._boot_write_state({
                "status": "failed",
                "last_transaction": txn_id,
                "last_error": err,
                "snapshot": str(snap.relative_to(self.ROOT_DIR)) if snap else None,
            })
            return False

    def boot_rollback(self) -> bool:
        """Rollback z snapshota (failed lub ręcznie ostatni)."""
        state = self._boot_read_state()
        snap_rel = state.get("snapshot")
        snap = None
        if snap_rel:
            cand = self.ROOT_DIR / snap_rel
            if cand.is_dir():
                snap = cand
        if snap is None:
            snaps = sorted(
                (s for s in (self.ROOT_DIR / "boot" / "snapshots").glob("*") if s.is_dir()),
                key=lambda p: p.name,
            )
            if not snaps:
                print(self.colorize("Brak snapshotów do rollbacku.", "yellow"))
                return False
            snap = snaps[-1]
            snap_rel = str(snap.relative_to(self.ROOT_DIR))
        print(self.colorize(f"Rollback z: {snap}", "cyan"))
        ok = self._boot_restore_snapshot(snap)
        if ok:
            if self._boot_instrukcja_path().exists():
                try:
                    self._boot_instrukcja_path().unlink()
                except Exception:
                    pass
            # wyczyść pending
            pending = self.ROOT_DIR / "boot" / "pending"
            if pending.is_dir():
                for child in list(pending.iterdir()):
                    try:
                        if child.is_dir():
                            shutil.rmtree(child)
                        else:
                            child.unlink()
                    except Exception:
                        pass
            self._boot_write_state({
                "status": "idle",
                "last_transaction": state.get("last_transaction"),
                "last_error": None,
                "snapshot": snap_rel,
            })
            print(self.colorize("✅ Rollback zakończony.", "green"))
        else:
            print(self.colorize("Rollback nieudany.", "red"))
        return ok

    def _stage_bin_transaction(self, bin_path: Path, package_name: str) -> dict:
        """
        .bin = ZIP z bin.json + plikami .py
        bin.json: {id, name, version}
        Wszystkie .py z archiwum → bin/<nazwa>.py, wersja → ver/
        """
        import zipfile
        bin_path = Path(bin_path)
        meta = {}
        try:
            with zipfile.ZipFile(bin_path, "r") as zf:
                if "bin.json" in zf.namelist():
                    meta = json.loads(zf.read("bin.json").decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Nie można odczytać .bin: {e}")

        pkg_id = (meta.get("id") or package_name or bin_path.stem).strip()
        version = str(meta.get("version") or "1.0")
        name = meta.get("name") or pkg_id

        pending = self.ROOT_DIR / "boot" / "pending" / pkg_id
        if pending.exists():
            shutil.rmtree(pending)
        pending.mkdir(parents=True, exist_ok=True)
        staged = pending / f"{pkg_id}.bin"
        shutil.copy2(bin_path, staged)
        content = pending / "content"
        content.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(staged, "r") as zf:
            zf.extractall(content)

        steps = []
        verify = []
        rollback = []
        for py in content.rglob("*.py"):
            rel_name = py.name  # always flat into bin/
            steps.append({
                "op": "copy",
                "src": str(py.relative_to(self.ROOT_DIR)).replace("\\", "/"),
                "dst": f"bin/{rel_name}",
            })
            verify.append({"op": "exists", "path": f"bin/{rel_name}"})
            rollback.append(f"bin/{rel_name}")

        if not steps:
            raise RuntimeError(".bin nie zawiera żadnego pliku .py")

        files_list = [s["dst"] for s in steps if s.get("op") == "copy"]
        steps.append({
            "op": "write_ver",
            "component": pkg_id,
            "version": version,
            "display_name": name,
            "pkg_type": "bin",
            "files": files_list,
        })
        rollback.extend([f"ver/{pkg_id}.json", f"ver/{pkg_id}.txt"])

        instr = {
            "id": f"bin-{pkg_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "action": "install",
            "package": pkg_id,
            "name": name,
            "version": version,
            "created": datetime.datetime.now().isoformat(),
            "steps": steps,
            "verify": verify,
            "rollback_paths": list(dict.fromkeys(rollback)),
        }
        self._boot_instrukcja_path().write_text(
            json.dumps(instr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._boot_write_state({
            "status": "pending",
            "last_transaction": instr["id"],
            "last_error": None,
        })
        return instr

    def _stage_py_transaction(self, py_path: Path, package_name: str) -> dict:
        """Pojedynczy .py z repo → bin/<name>.py przy sync."""
        py_path = Path(py_path)
        pkg_id = package_name or py_path.stem
        pending = self.ROOT_DIR / "boot" / "pending" / pkg_id
        if pending.exists():
            shutil.rmtree(pending)
        pending.mkdir(parents=True, exist_ok=True)
        staged = pending / f"{pkg_id}.py"
        shutil.copy2(py_path, staged)
        instr = {
            "id": f"py-{pkg_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "action": "install",
            "package": pkg_id,
            "name": pkg_id,
            "version": "1.0",
            "created": datetime.datetime.now().isoformat(),
            "steps": [
                {"op": "copy", "src": f"boot/pending/{pkg_id}/{pkg_id}.py", "dst": f"bin/{pkg_id}.py"},
                {"op": "write_ver", "component": pkg_id, "version": "1.0",
                 "display_name": pkg_id, "pkg_type": "py"},
            ],
            "verify": [{"op": "exists", "path": f"bin/{pkg_id}.py"}],
            "rollback_paths": [f"bin/{pkg_id}.py", f"ver/{pkg_id}.json", f"ver/{pkg_id}.txt"],
        }
        self._boot_instrukcja_path().write_text(
            json.dumps(instr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._boot_write_state({
            "status": "pending",
            "last_transaction": instr["id"],
            "last_error": None,
        })
        return instr

    def _stage_system_transaction(self, system_path: Path, package_name: str) -> dict:
        """
        .system = ZIP z system.json + plikami.
        system.json:
          {
            "id": "...", "version": "...",
            "targets": [{"from": "bin/x.py", "to": "bin/x.py"}, ...]
          }
        Sync kopiuje from → to względem ROOT (po extract do pending).
        """
        import zipfile
        system_path = Path(system_path)
        meta = {}
        try:
            with zipfile.ZipFile(system_path, "r") as zf:
                if "system.json" not in zf.namelist():
                    raise RuntimeError("Brak system.json w .system")
                meta = json.loads(zf.read("system.json").decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Nie można odczytać .system: {e}")

        pkg_id = (meta.get("id") or package_name or system_path.stem).strip()
        version = str(meta.get("version") or "1.0")
        name = meta.get("name") or pkg_id
        targets = meta.get("targets") or []
        if not targets:
            raise RuntimeError(".system bez targets[] — nie wiadomo co skopiować")

        pending_pkg = self.ROOT_DIR / "boot" / "pending" / pkg_id
        if pending_pkg.exists():
            shutil.rmtree(pending_pkg)
        pending_pkg.mkdir(parents=True, exist_ok=True)
        staged = pending_pkg / f"{pkg_id}.system"
        shutil.copy2(system_path, staged)

        # rozpakuj staging do pending/<id>/content/
        content = pending_pkg / "content"
        content.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(staged, "r") as zf:
            zf.extractall(content)

        steps = []
        verify = []
        rollback_paths = []
        for t in targets:
            src_rel = t.get("from") or t.get("src")
            dst_rel = t.get("to") or t.get("dst")
            if not src_rel or not dst_rel:
                continue
            steps.append({
                "op": "copy",
                "src": f"boot/pending/{pkg_id}/content/{src_rel}",
                "dst": dst_rel,
            })
            verify.append({"op": "exists", "path": dst_rel})
            rollback_paths.append(dst_rel)

        steps.append({
            "op": "write_ver",
            "component": pkg_id,
            "version": version,
            "display_name": name,
            "pkg_type": "system",
        })
        rollback_paths.append(f"ver/{pkg_id}.json")
        rollback_paths.append(f"ver/{pkg_id}.txt")

        instr = {
            "id": f"system-{pkg_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "action": "system",
            "package": pkg_id,
            "name": name,
            "version": version,
            "created": datetime.datetime.now().isoformat(),
            "steps": steps,
            "verify": verify,
            "rollback_paths": list(dict.fromkeys(rollback_paths)),
        }
        self._boot_instrukcja_path().write_text(
            json.dumps(instr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._boot_write_state({
            "status": "pending",
            "last_transaction": instr["id"],
            "last_error": None,
        })
        return instr

    def _stage_mars_transaction(self, mars_path: Path, package_name: str) -> dict:
        """
        Przygotuj instrukcja.json dla instalacji .mars:
        - extract do apps/<id>
        - opcjonalnie skopiuj entry do bin/
        - write_ver
        """
        import zipfile
        mars_path = Path(mars_path)
        manifest = {}
        try:
            with zipfile.ZipFile(mars_path, "r") as zf:
                names = zf.namelist()
                for cand in ("mars.json", "manifest.json"):
                    if cand in names:
                        manifest = json.loads(zf.read(cand).decode("utf-8"))
                        break
        except Exception as e:
            raise RuntimeError(f"Nie można odczytać .mars: {e}")

        pkg_id = (manifest.get("id") or package_name or mars_path.stem).strip()
        version = str(manifest.get("version") or "1.0")
        entry = manifest.get("entry")
        name = manifest.get("name") or pkg_id

        # stage kopia archiwum w pending
        pending_pkg = self.ROOT_DIR / "boot" / "pending" / pkg_id
        if pending_pkg.exists():
            shutil.rmtree(pending_pkg)
        pending_pkg.mkdir(parents=True, exist_ok=True)
        staged_mars = pending_pkg / f"{pkg_id}.mars"
        shutil.copy2(mars_path, staged_mars)

        steps = [
            {"op": "mkdir", "path": "apps"},
            {"op": "extract_mars", "src": f"boot/pending/{pkg_id}/{pkg_id}.mars", "dst": f"apps/{pkg_id}"},
            {"op": "write_ver", "component": pkg_id, "version": version,
             "display_name": name, "pkg_type": "app",
             "files": [f"apps/{pkg_id}", f"bin/{pkg_id}.py"]},
        ]
        verify = [
            {"op": "exists", "path": f"apps/{pkg_id}"},
        ]
        # mars.json lub manifest w apps
        verify.append({"op": "exists", "path": f"apps/{pkg_id}/mars.json"})

        if entry:
            # jeśli entry jest .py — zrób wrapper w /bin/<id>.py
            bin_name = f"{pkg_id}.py"
            steps.append({
                "op": "write_text",
                "path": f"bin/{bin_name}",
                "content": (
                    f"#!/usr/bin/env python3\n"
                    f"# Auto-wrapper OSmars dla {name}\n"
                    f"import runpy\n"
                    f"from pathlib import Path\n"
                    f"root = Path(__file__).resolve().parents[1]\n"
                    f"entry = root / 'apps' / '{pkg_id}' / '{entry}'\n"
                    f"runpy.run_path(str(entry), run_name='__main__')\n"
                ),
            })
            verify.append({"op": "exists", "path": f"bin/{bin_name}"})

        instr = {
            "id": f"install-{pkg_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "action": "install",
            "package": pkg_id,
            "name": name,
            "version": version,
            "created": datetime.datetime.now().isoformat(),
            "steps": steps,
            "verify": verify,
            "rollback_paths": [f"apps/{pkg_id}", f"bin/{pkg_id}.py", f"ver/{pkg_id}.txt"],
        }
        self._boot_instrukcja_path().write_text(
            json.dumps(instr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._boot_write_state({
            "status": "pending",
            "last_transaction": instr["id"],
            "last_error": None,
        })
        return instr


    def cmd_auto_sync(self, args=None):
        """auto-sync on | off | status — sync zaraz po pobraniu paczki."""
        args = args or []
        key = "auto_sync_after_install"
        if not args or args[0].lower() in ("status", "show", "?"):
            on = bool(self.config.get(key, False))
            boot = bool(self.config.get("auto_sync_on_boot", True))
            print(self.colorize(f"auto-sync after install: {'ON' if on else 'OFF'}", "cyan"))
            print(self.colorize(f"auto-sync on boot:       {'ON' if boot else 'OFF'}", "cyan"))
            print("Użycie: auto-sync on | off | status")
            return
        val = args[0].lower()
        if val in ("on", "1", "true", "yes", "enable"):
            self.config[key] = True
            self.save_config(self.config)
            print(self.colorize("auto-sync after install: ON", "green"))
        elif val in ("off", "0", "false", "no", "disable"):
            self.config[key] = False
            self.save_config(self.config)
            print(self.colorize("auto-sync after install: OFF", "yellow"))
        elif val in ("boot-on", "boot_on"):
            self.config["auto_sync_on_boot"] = True
            self.save_config(self.config)
            print(self.colorize("auto-sync on boot: ON", "green"))
        elif val in ("boot-off", "boot_off"):
            self.config["auto_sync_on_boot"] = False
            self.save_config(self.config)
            print(self.colorize("auto-sync on boot: OFF", "yellow"))
        else:
            print(self.colorize("Użycie: auto-sync on | off | status | boot-on | boot-off", "yellow"))

    def from_mars_uninstall(self, package_name: str):
        """Usuń zainstalowaną paczkę (apps, bin, ver, downloads, pending)."""
        pkg = (package_name or "").strip()
        for suf in (".mars", ".system", ".bin", ".py"):
            if pkg.lower().endswith(suf):
                pkg = pkg[: -len(suf)]
                break
        pkg = pkg.strip()
        ver_dir = self.ROOT_DIR / "ver"
        apps_dir = self.ROOT_DIR / "apps"

        if not pkg:
            print(self.colorize("Użycie: from mars uninstall <nazwa>", "yellow"))
            installed = sorted(ver_dir.glob("*.json")) if ver_dir.is_dir() else []
            if apps_dir.is_dir():
                for d in sorted(apps_dir.iterdir()):
                    if d.is_dir() and not (ver_dir / f"{d.name}.json").exists():
                        installed.append(d)  # show name only later
            if ver_dir.is_dir():
                for f in sorted(ver_dir.glob("*.json")):
                    try:
                        d = json.loads(f.read_text(encoding="utf-8"))
                        print(f"  {d.get('id')}  v{d.get('version')}  ({d.get('name')})  type={d.get('type')}")
                    except Exception:
                        print(f"  {f.stem}")
            if apps_dir.is_dir():
                for d in sorted(apps_dir.iterdir()):
                    if d.is_dir():
                        print(f"  apps/{d.name}/")
            return

        # dopasuj id bez względu na wielkość liter
        real_id = pkg
        for candidate in list((ver_dir.glob("*.json") if ver_dir.is_dir() else [])) + \
                         list((apps_dir.iterdir() if apps_dir.is_dir() else [])):
            name = candidate.stem if candidate.suffix == ".json" else candidate.name
            if name.lower() == pkg.lower():
                real_id = name
                break

        removed = []
        files_extra = []
        vjson = ver_dir / f"{real_id}.json"
        if vjson.exists():
            try:
                meta = json.loads(vjson.read_text(encoding="utf-8"))
                files_extra = list(meta.get("files") or [])
            except Exception:
                pass

        targets = [
            self.ROOT_DIR / "apps" / real_id,
            self.ROOT_DIR / "bin" / f"{real_id}.py",
            self.ROOT_DIR / "ver" / f"{real_id}.json",
            self.ROOT_DIR / "ver" / f"{real_id}.txt",
            self.ROOT_DIR / "boot" / "pending" / real_id,
            self.ROOT_DIR / "boot" / "updates" / f"{real_id}.mars",
            self.ROOT_DIR / "boot" / "updates" / f"{real_id}.system",
            self.ROOT_DIR / "boot" / "updates" / f"{real_id}.bin",
            self.ROOT_DIR / "files" / "Downloads" / f"{real_id}.mars",
            self.ROOT_DIR / "files" / "Downloads" / f"{real_id}.system",
            self.ROOT_DIR / "files" / "Downloads" / f"{real_id}.bin",
        ]
        for rel in files_extra:
            targets.append(self.ROOT_DIR / str(rel).replace("\\", "/").lstrip("/"))

        # usuń też inne bin/*.py zainstalowane jako część paczki (po nazwie w ver files)
        seen = set()
        for path in targets:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            try:
                if path.is_file():
                    path.unlink()
                    try:
                        removed.append(str(path.relative_to(self.ROOT_DIR)))
                    except Exception:
                        removed.append(str(path))
                elif path.is_dir():
                    shutil.rmtree(path)
                    try:
                        removed.append(str(path.relative_to(self.ROOT_DIR)) + "/")
                    except Exception:
                        removed.append(str(path) + "/")
            except Exception as e:
                print(self.colorize(f"  nie usunięto {path}: {e}", "yellow"))

        if removed:
            print(self.colorize(f"✅ Odinstalowano '{real_id}':", "green"))
            for r in removed:
                print(f"   - {r}")
        else:
            print(self.colorize(f"Nic nie znaleziono dla '{pkg}'.", "yellow"))

    def _version_tuple(self, v: str):
        parts = []
        for p in str(v or "0").replace("-", ".").split("."):
            try:
                parts.append(int("".join(c for c in p if c.isdigit()) or "0"))
            except Exception:
                parts.append(0)
        return tuple(parts) if parts else (0,)

    def _fetch_remote_packages(self) -> list:
        """Pobierz listę paczek z API serwera."""
        base = self.config.get("mars_repo_url", "http://yourrepo/").rstrip("/")
        import urllib.request
        url = f"{base}/api/packages"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("packages") or []
        except Exception as e:
            print(self.colorize(f"API niedostępne ({url}): {e}", "red"))
            return []

    def from_mars_update(self, package_name: str = ""):
        """Porównaj ver/*.json z API i zaktualizuj nowsze paczki."""
        only = (package_name or "").strip()
        for suf in (".mars", ".system", ".bin", ".py"):
            if only.lower().endswith(suf):
                only = only[: -len(suf)]
                break
        only = only.strip().lower()

        remote = self._fetch_remote_packages()
        if not remote:
            print(self.colorize("Brak paczek z serwera / błąd API.", "yellow"))
            return

        remote_map = {}
        for p in remote:
            stem = (p.get("stem") or Path(p.get("name", "")).stem).lower()
            # preferuj wpis z wyższą wersją
            prev = remote_map.get(stem)
            if not prev or self._version_tuple(p.get("version")) > self._version_tuple(prev.get("version")):
                remote_map[stem] = p

        ver_dir = self.ROOT_DIR / "ver"
        local_ids = set()
        if ver_dir.is_dir():
            for f in ver_dir.glob("*.json"):
                local_ids.add(f.stem.lower())

        targets = [only] if only else sorted(local_ids)
        if not targets:
            print(self.colorize("Brak lokalnych wpisów w ver/ — podaj nazwę albo zainstaluj coś.", "yellow"))
            return

        # jeśli wisi failed/pending — spróbuj wyczyścić failed albo ostrzeż
        st = self._boot_read_state().get("status")
        if st == "pending":
            print(self.colorize("Jest pending transakcja — najpierw: sync  albo  rollback", "yellow"))
            return

        updated = 0
        # tymczasowo włącz auto-sync żeby każda paczka się domknęła
        prev_auto = self.config.get("auto_sync_after_install", False)
        self.config["auto_sync_after_install"] = True
        try:
            for pid in targets:
                local_ver = "0"
                vfile = ver_dir / f"{pid}.json"
                # case-insensitive local file
                if not vfile.exists() and ver_dir.is_dir():
                    for f in ver_dir.glob("*.json"):
                        if f.stem.lower() == pid:
                            vfile = f
                            break
                if vfile.exists():
                    try:
                        local_ver = str(json.loads(vfile.read_text(encoding="utf-8")).get("version") or "0")
                    except Exception:
                        pass
                rem = remote_map.get(pid)
                if not rem:
                    print(f"  {pid}: brak na serwerze (lokalnie v{local_ver})")
                    continue
                rver = str(rem.get("version") or "0")
                if self._version_tuple(rver) > self._version_tuple(local_ver):
                    print(self.colorize(f"  {pid}: {local_ver} → {rver}  aktualizuję…", "cyan"))
                    self.from_mars_install(pid)
                    # upewnij się że pending domknięty
                    if self._boot_has_pending():
                        self.boot_sync()
                    updated += 1
                else:
                    print(f"  {pid}: v{local_ver} — aktualne (serwer v{rver or '?'})")
        finally:
            self.config["auto_sync_after_install"] = prev_auto

        if updated:
            print(self.colorize(f"Zaktualizowano paczek: {updated}", "green"))
        else:
            print(self.colorize("Wszystko aktualne.", "green"))

    def from_mars_install(self, package_name: str):
        """
        from mars install <nazwa>
        1) pobierz <nazwa>.mars z repo
        2) zapisz do boot/updates/
        3) przygotuj boot/instrukcja.json (pending)
        4) użytkownik / auto: sync
        """
        pkg = (package_name or "").strip()
        if not pkg:
            print(self.colorize("Użycie: from mars install <nazwa>", "yellow"))
            return

        base_url = self.config.get("mars_repo_url", "http://yourrepo/").rstrip("/")
        stem = pkg
        lower = stem.lower()
        for suf in (".mars", ".system", ".bin", ".py", ".pkg", ".tar.gz", ".tgz", ".zip"):
            if lower.endswith(suf):
                stem = stem[: -len(suf)]
                break
        stem = stem.strip()
        if not stem:
            print(self.colorize("Użycie: from mars install <nazwa>", "yellow"))
            return

        if self._boot_has_pending() and self._boot_read_state().get("status") == "pending":
            print(self.colorize(
                "Jest już oczekująca transakcja w /boot. "
                "Najpierw: sync  albo  rollback",
                "yellow",
            ))
            return

        # Nowa struktura serwera:
        #   /mars/<name>.mars  /system/<name>.system  /bin/<name>.bin
        # + kompatybilność /repo/<name>.ext
        updates_dir = self.ROOT_DIR / "boot" / "updates"
        downloads_dir = self.ROOT_DIR / "files" / "Downloads"
        updates_dir.mkdir(parents=True, exist_ok=True)
        downloads_dir.mkdir(parents=True, exist_ok=True)

        try:
            import urllib.request
            import urllib.error
        except ImportError:
            print(self.colorize("urllib niedostępne", "red"))
            return

        candidates = [
            ("mars", f"{stem}.mars"),
            ("system", f"{stem}.system"),
            ("bin", f"{stem}.bin"),
            # legacy flat repo
            ("repo", f"{stem}.mars"),
            ("repo", f"{stem}.system"),
            ("repo", f"{stem}.bin"),
            ("repo", f"{stem}.py"),
        ]

        dest = None
        found_name = None
        found_kind = None
        for channel, fname in candidates:
            url = f"{base_url}/{channel}/{fname}"
            print(self.colorize(f"Szukam: {fname}  ({url})", "cyan"))
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status not in (200, 301, 302):
                        continue
                dl = downloads_dir / fname
                print(self.colorize(f"Znaleziono: {fname}", "green"))
                print(self.colorize(f"Pobieram → Downloads/{fname}", "cyan"))
                urllib.request.urlretrieve(url, str(dl))
                size = dl.stat().st_size
                print(self.colorize(f"✅ Pobrano '{fname}' ({size} B) do files/Downloads/", "green"))
                dest = updates_dir / fname
                shutil.copy2(dl, dest)
                found_name = fname
                found_kind = channel if channel != "repo" else (
                    "mars" if fname.endswith(".mars") else
                    "system" if fname.endswith(".system") else
                    "bin" if fname.endswith(".bin") else "py"
                )
                break
            except Exception:
                continue

        if not dest or not found_name:
            print(self.colorize(
                f"❌ Nie znaleziono '{stem}' (.mars/.system/.bin) w repo serwera.",
                "red",
            ))
            print(self.colorize(f"   Sprawdź: {base_url}/  (foldery mars/ system/ bin/)", "yellow"))
            return

        try:
            if found_name.endswith(".system") or found_kind == "system":
                instr = self._stage_system_transaction(dest, stem)
            elif found_name.endswith(".bin") or found_kind == "bin":
                instr = self._stage_bin_transaction(dest, stem)
            elif found_name.endswith(".py") or found_kind == "py":
                instr = self._stage_py_transaction(dest, stem)
            else:
                # .mars → Downloads (już jest); instalacja do apps tylko gdy auto_install_mars
                if self.config.get("auto_install_mars"):
                    instr = self._stage_mars_transaction(dest, stem)
                else:
                    print(self.colorize(
                        "📦 .mars zapisane w Downloads. "
                        "Otwórz z pulpitu/Downloads albo PPM → Zainstaluj.",
                        "green",
                    ))
                    return

            print(self.colorize(f"📋 Transakcja przygotowana: {instr['id']}", "cyan"))
            print(f"   package: {instr.get('package')}  v{instr.get('version')}")
            print(self.colorize("   Plik w: files/Downloads/" + found_name, "green"))
            print(self.colorize("   Następny krok:  sync", "yellow"))
            print(self.colorize("   (lub restart — auto_sync_on_boot zastosuje instrukcję)", "yellow"))
            if self.config.get("auto_sync_after_install"):
                print(self.colorize("   auto_sync_after_install=True → sync teraz…", "cyan"))
                self.boot_sync()
        except Exception as e:
            print(self.colorize(f"[ERR] Nie udało się przygotować instrukcji: {e}", "red"))

    # ---------------- Utilities ----------------
    def search_files(self, pattern, directory=None):
        if directory is None:
            directory = self.current_dir
        directory = Path(directory)
        matches = []
        try:
            for root, dirs, files in os.walk(str(directory)):
                for file in files:
                    if pattern.lower() in file.lower():
                        matches.append(str(Path(root) / file))
        except Exception:
            pass
        return matches

    def get_file_info(self, filepath):
        try:
            p = Path(filepath)
            if not p.exists():
                return None
            stat = p.stat()
            size = stat.st_size
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            return {
                'size': size,
                'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
                'readable': os.access(str(p), os.R_OK),
                'writable': os.access(str(p), os.W_OK),
                'executable': os.access(str(p), os.X_OK)
            }
        except Exception:
            return None

    # ---------------- Main loop ----------------
    def run(self):
        """Start → sprawdź /boot transakcje → GUI Selector → Recovery."""
        try:
            if not (self.ROOT_DIR / "system" / "initialized").exists():
                self.first_run_setup()

            # Plan: Recovery sprawdza /boot i stosuje instrukcje przed GUI
            self.boot_check_on_startup()

            # GUI Selector
            # Zwraca False = wyjście, True = wejście do Recovery
            continue_to_recovery = self.gui_selector()
            if not continue_to_recovery:
                return

            # Recovery Terminal loop
            while True:
                try:
                    command = input(self.get_prompt()).strip()
                    if not self.execute_command(command):
                        break
                except KeyboardInterrupt:
                    print(self.colorize("\nUse 'exit' to quit OSmars PC", 'yellow'))
                    continue
                except EOFError:
                    print(self.colorize("\nGoodbye!", 'yellow'))
                    break
        except Exception as e:
            print(self.colorize(f"Critical error: {e}", 'red'))
            import traceback
            traceback.print_exc()
        finally:
            self.save_history()

    def first_run_setup(self):
        print(self.colorize("\n=== First Run Setup ===", 'cyan'))
        print("Setting up OSmars PC for the first time...")

        try:
            examples_dir = self.ROOT_DIR / "files" / "examples"
            examples_dir.mkdir(parents=True, exist_ok=True)

            sample_py = examples_dir / "hello.py"
            sample_py.write_text('''#!/usr/bin/env python3
"""
Sample OSmars PC Program
"""

def main():
    print("🚀 Welcome to OSmars PC!")
    print("This file is located in the examples directory")
    print("You can run it with: boot hello.py")

    name = input("What's your name? ")
    print(f"Nice to meet you, {name}!")

if __name__ == "__main__":
    main()
''', encoding='utf-8')

            readme = self.ROOT_DIR / "README.txt"
            readme.write_text('''OSmars PC - Enhanced Terminal System with PySide6 GUI
======================================================

Welcome to OSmars PC! This is an advanced terminal system with PySide6 desktop environment.

Basic commands:
- help          - Show help
- ls -l         - List files with details
- cd <dir>      - Change directory
- edit <file>   - Edit file (nano-like editor)
- boot <file>   - Run Python file
- find <pattern>- Search files
- tree          - Directory structure
- bootsys       - Launch PySide6 GUI desktop

Advanced features:
- Command history (history)
- Aliases (alias name=command)
- Configuration (config)
- Syntax coloring
- Auto-save
- PySide6 desktop environment with embedded browser
- File manager, notepad, calculator apps

Package Management:
- sudo pacman -S pyside6   - Install PySide6 for GUI support

Examples are located in files/examples/
Use 'bootsys' to launch the graphical desktop environment!

The GUI system is generated as boot/desktop/gui_system.py
''', encoding='utf-8')

            (self.ROOT_DIR / "system" / "initialized").write_text(str(datetime.datetime.now()), encoding='utf-8')
            print(self.colorize("✓ Setup completed!", 'green'))
            print(f"Check out the examples in {self.colorize('files/examples/', 'blue')}")
            print(f"Use {self.colorize('bootsys', 'yellow')} to launch the GUI desktop!")
            print(f"GUI system file: {self.colorize('boot/desktop/gui_system.py', 'cyan')}")
            print()

        except Exception as e:
            print(self.colorize(f"Setup error: {e}", 'red'))


# ---------------- Entrypoint ----------------
def main():
    if os.name == 'nt':
        try:
            import sys
            if sys.stdout.encoding.lower() != 'utf-8':
                import io
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

    try:
        os_mars = OSMarsPC()
        os_mars.run()
    except KeyboardInterrupt:
        print("\n\nOSmars PC interrupted by user.")
    except Exception as e:
        print(f"Critical error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
