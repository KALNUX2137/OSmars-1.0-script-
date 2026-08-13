#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSmars PC GUI System v1.0
Professional Desktop Environment with Enhanced Features
Fixed theme switching and terminal display issues
"""
# ==============================
# WYMAGANE IMPORTY DLA GUI
# ==============================
try:
    from PySide6.QtCore import (
        QObject, Qt, QTimer, QUrl, QRect, QPoint, QSize, Signal,
        QMimeData, QEvent, QThread, QDir, QCoreApplication, QSettings
    )
    from PySide6.QtGui import (
        QDesktopServices, QCursor, QIcon, QPixmap, QFont, QAction,
        QDrag, QPainter, QColor, QPalette, QClipboard, QKeySequence,
        QShortcut, QBrush, QPen, QLinearGradient, QRadialGradient
    )
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QListWidget, QMenu, QTextEdit, QPlainTextEdit, QLineEdit, QGridLayout,
        QTreeView, QFileSystemModel, QDialog, QMessageBox, QInputDialog,
        QTabWidget, QSplitter, QToolBar, QStatusBar, QFrame, QScrollArea, QFileDialog, QSpinBox,
        QGroupBox, QToolButton, QComboBox, QSlider, QProgressBar, QSplashScreen,
        QGraphicsDropShadowEffect, QToolTip, QStyle, QStyleOptionButton
    )

    QT_AVAILABLE = True
except ImportError as e:
    print(f"Error importing PySide6: {e}")
    QT_AVAILABLE = False

# Create dummy classes to prevent further errors
if not QT_AVAILABLE:
    class QObject: pass


    class Signal:
        def __init__(self, *args): pass

        def emit(self, *args): pass

        def connect(self, *args): pass


    class QTimer(QObject):
        def __init__(self, *args): super().__init__()

        def start(self, *args): pass

        def stop(self): pass

        @staticmethod
        def singleShot(*args): pass


    class QWidget: pass


    class QLabel(QWidget): pass


    class QMessageBox:
        Yes, No, Cancel = 1, 2, 3

        @staticmethod
        def question(*args): return QMessageBox.Yes

        @staticmethod
        def critical(*args): pass

        @staticmethod
        def information(*args): pass

        @staticmethod
        def warning(*args): pass


    class QApplication:
        def __init__(self, *args): pass

        @staticmethod
        def instance(): return QApplication()

        def exec(self): return 0

        def quit(self): pass

        @staticmethod
        def setPalette(*args): pass

        @staticmethod
        def palette(): return None

        @staticmethod
        def clipboard(): return None

        @staticmethod
        def primaryScreen():
            class Screen:
                def availableGeometry(self): return QRect(0, 0, 1920, 1080)

            return Screen()

        @staticmethod
        def setStyle(*args): pass

        @staticmethod
        def setWindowIcon(*args): pass

import os
import sys
import json
import datetime
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from enum import Enum
import logging
import re
import math
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("osmars_gui.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("OSmars-GUI")


class ThemeMode(Enum):
    """Desktop theme modes"""
    DARK = "dark"
    LIGHT = "light"


class WindowEventType(Enum):
    """Types of window events for filtering"""
    MOVE = "move"
    RESIZE = "resize"
    SHOW = "show"
    HIDE = "hide"
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class ApplicationType(Enum):
    """Types of applications that can be launched"""
    FILE_EXPLORER = "file_explorer"
    BROWSER = "browser"
    TERMINAL = "terminal"
    NOTEPAD = "notepad"
    CALCULATOR = "calculator"
    DOWNLOADS = "downloads"
    SETTINGS = "settings"


class DesktopIconType(Enum):
    """Types of desktop icons"""
    SYSTEM = "system"
    FILE = "file"
    FOLDER = "folder"
    APPLICATION = "application"


class WindowManager:
    """Fallback window manager to maintain compatibility"""

    def __init__(self, desktop_window):
        self.desktop_window = desktop_window
        self.windows = []
        self.active_window = None

    def add_window(self, window):
        if window not in self.windows:
            self.windows.append(window)

    def remove_window(self, window):
        if window in self.windows:
            self.windows.remove(window)

    def activate_window(self, window):
        self.active_window = window
        if hasattr(window, 'raise_'):
            window.raise_()
        if hasattr(window, 'activateWindow'):
            window.activateWindow()


class WindowEventFilter(QObject):
    """Event filter for window movements and visibility updates"""

    def __init__(self, desktop_window):
        super().__init__()
        self.desktop_window = desktop_window

    def eventFilter(self, obj, event):
        """Filter window events for visibility updates"""
        event_type = None
        if event.type() == QEvent.Move:
            event_type = WindowEventType.MOVE
        elif event.type() == QEvent.Resize:
            event_type = WindowEventType.RESIZE
        elif event.type() == QEvent.Show:
            event_type = WindowEventType.SHOW
        elif event.type() == QEvent.Hide:
            event_type = WindowEventType.HIDE
        if event_type:
            QTimer.singleShot(0, self.desktop_window.update_icon_visibility)
        return super().eventFilter(obj, event)


class ManagedWindow(QWidget):
    """Managed window with title bar and window controls"""
    closed = Signal(object)
    minimized_changed = Signal(object, bool)
    maximized_changed = Signal(object, bool)

    def __init__(self, title: str, content_widget: QWidget, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.content_widget = content_widget
        self.is_maximized = False
        self.is_minimized = False
        self.normal_geometry = None
        self.dragging = False
        self.drag_position = QPoint()
        self.task_button = None
        self.theme_mode = ThemeMode.DARK
        self._setup_ui(title)
        self.resize(900, 650)

    def _setup_ui(self, title: str):
        """Setup window UI with proper styling"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title_bar = self._create_title_bar(title)
        layout.addWidget(title_bar)
        content_frame = QFrame()
        content_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self.content_widget)
        layout.addWidget(content_frame, 1)
        self.setStyleSheet("""
            ManagedWindow {
                background-color: transparent;
                border-radius: 8px;
            }
        """)

    def _create_title_bar(self, title: str) -> QWidget:
        """Create styled window title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 0, 8, 0)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        btn_minimize = self._create_control_button("−", self.toggle_minimize)
        self.btn_maximize = self._create_control_button("□", self.toggle_maximize)
        btn_close = self._create_control_button("×", self.close, is_close=True)
        title_layout.addWidget(btn_minimize)
        title_layout.addWidget(self.btn_maximize)
        title_layout.addWidget(btn_close)
        title_bar.mousePressEvent = self._title_bar_mouse_press
        title_bar.mouseMoveEvent = self._title_bar_mouse_move
        title_bar.mouseReleaseEvent = self._title_bar_mouse_release
        title_bar.mouseDoubleClickEvent = lambda e: self.toggle_maximize()
        return title_bar

    def _create_control_button(self, text: str, callback, is_close: bool = False) -> QPushButton:
        """Create styled window control button"""
        btn = QPushButton(text)
        btn.setFixedSize(40, 32)
        font_size = "28px" if is_close else "20px" if text == "−" else "16px"
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: {font_size};
                font-weight: bold;
                margin: 2px;
            }}
        """)
        btn.clicked.connect(callback)
        btn.setFocusPolicy(Qt.NoFocus)
        return btn

    def _title_bar_mouse_press(self, event):
        if event.button() == Qt.LeftButton and not self.is_maximized:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _title_bar_mouse_move(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            self._update_icon_visibility()
            event.accept()

    def _title_bar_mouse_release(self, event):
        self.dragging = False
        event.accept()

    def _update_icon_visibility(self):
        desktop_window = self._get_desktop_window()
        if desktop_window and hasattr(desktop_window, 'update_icon_visibility'):
            desktop_window.update_icon_visibility()

    def _get_desktop_window(self):
        desktop_window = self.parent()
        while desktop_window and hasattr(desktop_window, 'parent') and desktop_window.parent():
            desktop_window = desktop_window.parent()
        return desktop_window

    def toggle_minimize(self):
        self.is_minimized = not self.is_minimized
        self.setVisible(not self.is_minimized)
        self.minimized_changed.emit(self, self.is_minimized)
        if self.task_button:
            self.task_button.setProperty("minimized", self.is_minimized)
            self.task_button.style().polish(self.task_button)

    def toggle_maximize(self):
        desktop_window = self._get_desktop_window()
        if not desktop_window:
            return
        if self.is_maximized:
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            self.is_maximized = False
            self.btn_maximize.setText("□")
            self.maximized_changed.emit(self, False)
        else:
            self.normal_geometry = self.geometry()
            screen_rect = desktop_window.geometry()
            available_rect = QRect(
                screen_rect.x(),
                screen_rect.y(),
                screen_rect.width(),
                screen_rect.height() - 56
            )
            self.setGeometry(available_rect)
            self.is_maximized = True
            self.btn_maximize.setText("❐")
            self.maximized_changed.emit(self, True)
            self._update_icon_visibility()
            self.raise_()

    def bring_to_front(self):
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if not self.is_maximized and self.normal_geometry:
            self.normal_geometry = self.geometry()
        self.closed.emit(self)
        event.accept()

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "#2d2d30" if is_dark else "#ffffff"
        text_color = "white" if is_dark else "black"
        gradient_start = "#3b82f6" if is_dark else "#4d648d"
        gradient_end = "#2563eb" if is_dark else "#3a517d"
        title_bar_style = f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {gradient_start}, stop:1 {gradient_end});
                color: white;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """
        title_bar = self.layout().itemAt(0).widget()
        title_bar.setStyleSheet(title_bar_style)
        self.title_label.setStyleSheet(f"font-weight: bold; color: white; font-size: 12px;")
        control_buttons = [
            self.layout().itemAt(0).widget().layout().itemAt(i).widget()
            for i in range(self.layout().itemAt(0).widget().layout().count())
            if isinstance(self.layout().itemAt(0).widget().layout().itemAt(i).widget(), QPushButton)
        ]
        for btn in control_buttons:
            hover_color = "#e81123" if btn.text() == "×" else "rgba(255,255,255,0.2)"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: white;
                    border: none;
                    font-size: {'28px' if btn.text() == "×" else '20px' if btn.text() == "−" else '16px'};
                    font-weight: bold;
                    margin: 2px;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                    border-radius: 4px;
                }}
            """)
        content_bg = "#1e1e1e" if is_dark else "#f5f5f5"
        content_border = "#3e3e42" if is_dark else "#e0e0e0"
        self.content_widget.setStyleSheet(f"""
            background-color: {content_bg};
            color: {text_color};
            border: 1px solid {content_border};
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        """)
        if hasattr(self.content_widget, 'apply_theme'):
            self.content_widget.apply_theme(theme_mode)


class DesktopIcon(QWidget):
    """Desktop icon with drag & drop support"""
    double_clicked = Signal(str, str)
    position_changed = Signal(object)
    GRID_SIZE = 96
    ICON_SIZE = 84
    MARGIN = 16
    COL_WIDTH = 100
    ROW_HEIGHT = 110

    def __init__(self, name: str, icon_text: str, path: Optional[str] = None,
                 icon_type: DesktopIconType = DesktopIconType.SYSTEM, parent=None,
                 icon_pixmap: Optional[QPixmap] = None):
        super().__init__(parent)
        self.name = name
        self.path = path or ""
        self.icon_type = icon_type
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.theme_mode = ThemeMode.DARK
        self._icon_pixmap = icon_pixmap
        self._setup_ui(icon_text)

    def _setup_ui(self, icon_text: str):
        # stała szerokość kolumny, wysokość pod ikonę + 2 linie tekstu
        self.setFixedSize(self.COL_WIDTH, self.ROW_HEIGHT)
        self.setCursor(Qt.SizeAllCursor)
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(2)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedHeight(56)
        if self._icon_pixmap is not None and not self._icon_pixmap.isNull():
            # ikony z .mars — bez powiększania ponad 48
            scaled = self._icon_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_label.setPixmap(scaled)
        else:
            self.icon_label.setText(icon_text)
        layout.addWidget(self.icon_label)
        self.name_label = QLabel(self.name)
        self.name_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.name_label.setWordWrap(True)
        self.name_label.setFixedWidth(self.COL_WIDTH - 8)
        self.name_label.setMaximumHeight(44)
        layout.addWidget(self.name_label)
        self.apply_theme(ThemeMode.DARK)

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "rgba(0, 0, 0, 0.7)" if is_dark else "rgba(255, 255, 255, 0.7)"
        text_color = "white" if is_dark else "black"
        text_shadow = "0px 1px 2px rgba(0,0,0,0.5)" if is_dark else "0px 1px 2px rgba(255,255,255,0.5)"
        icon_size = "52px"
        if hasattr(self, "icon_label") and self.icon_label.pixmap() is None:
            self.icon_label.setStyleSheet(f"font-size: {icon_size}; color: {text_color};")
        self.name_label.setStyleSheet(f"""
            color: {text_color};
            background: {bg_color};
            padding: 3px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 500;
            text-shadow: {text_shadow};
        """)

    def snap_to_grid(self, pos: QPoint) -> QPoint:
        # kolumny w pionie (klasyczny pulpit): stały COL_WIDTH / ROW_HEIGHT
        col = max(0, round((pos.x() - self.MARGIN) / self.COL_WIDTH))
        row = max(0, round((pos.y() - self.MARGIN) / self.ROW_HEIGHT))
        return QPoint(self.MARGIN + col * self.COL_WIDTH, self.MARGIN + row * self.ROW_HEIGHT)

    def is_position_occupied(self, pos: QPoint) -> bool:
        desktop_window = self._get_desktop_window()
        if not desktop_window or not hasattr(desktop_window, "desktop_icons"):
            return False
        test = QRect(pos.x(), pos.y(), self.COL_WIDTH - 4, self.ROW_HEIGHT - 4)
        for icon in desktop_window.desktop_icons:
            if icon is self or not icon.isVisible():
                continue
            other = QRect(icon.x(), icon.y(), self.COL_WIDTH - 4, self.ROW_HEIGHT - 4)
            if test.intersects(other):
                return True
        return False

    def find_free_position(self, preferred_pos: QPoint) -> QPoint:
        preferred_pos = self.snap_to_grid(preferred_pos)
        if not self.is_position_occupied(preferred_pos):
            return preferred_pos
        # szukaj w dół kolumny, potem następna kolumna (układ pionowy)
        desktop_window = self._get_desktop_window()
        max_h = 600
        max_w = 1200
        if desktop_window is not None:
            try:
                max_h = max(200, desktop_window.desktop_area.height() - self.ROW_HEIGHT)
                max_w = max(200, desktop_window.desktop_area.width() - self.COL_WIDTH)
            except Exception:
                pass
        for col in range(0, 20):
            for row in range(0, 30):
                test = QPoint(self.MARGIN + col * self.COL_WIDTH, self.MARGIN + row * self.ROW_HEIGHT)
                if test.y() > max_h or test.x() > max_w:
                    continue
                if not self.is_position_occupied(test):
                    return test
        return preferred_pos

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_start_pos = event.position().toPoint()
            self._drag_origin = self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = event.position().toPoint() - self.drag_start_pos
            if not self.dragging and delta.manhattanLength() >= QApplication.startDragDistance():
                self.dragging = True
                self.raise_()
            if self.dragging:
                # swobodne przesuwanie (snap dopiero przy puszczeniu)
                new_pos = self.mapToParent(event.position().toPoint() - self.drag_start_pos)
                new_pos.setX(max(0, new_pos.x()))
                new_pos.setY(max(0, new_pos.y()))
                self.move(new_pos)
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            snapped = self.snap_to_grid(self.pos())
            final = self.find_free_position(snapped)
            self.move(final)
            self.position_changed.emit(self)
            event.accept()
            return
        self.dragging = False
        super().mouseReleaseEvent(event)

    def _start_drag(self, event):
        # legacy no-op — przeciąganie jest w mouseMoveEvent
        pass

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.name, self.path)
            event.accept()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        desktop_window = self._get_desktop_window()
        if desktop_window and hasattr(desktop_window, 'show_icon_context_menu'):
            desktop_window.show_icon_context_menu(self, event.globalPos())
        event.accept()

    def dragEnterEvent(self, event):
        if self.path and Path(self.path).is_dir() and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not (self.path and Path(self.path).is_dir()):
            return
        urls = event.mimeData().urls()
        if not urls:
            return
        try:
            desktop_window = self._get_desktop_window()
            target_path = Path(self.path)
            files_moved = 0
            for url in urls:
                source_path = Path(url.toLocalFile())
                if not source_path.exists():
                    continue
                dest_path = target_path / source_path.name
                counter = 1
                while dest_path.exists():
                    name_parts = source_path.stem, source_path.suffix
                    dest_path = target_path / f"{name_parts[0]} ({counter}){name_parts[1]}"
                    counter += 1
                if source_path.is_dir():
                    shutil.copytree(source_path, dest_path)
                else:
                    shutil.copy2(source_path, dest_path)
                files_moved += 1
            if files_moved > 0:
                event.acceptProposedAction()
                if desktop_window:
                    desktop_window.status_message(f"Moved {files_moved} item(s) to {target_path.name}")
        except Exception as e:
            logger.error(f"Error moving files to folder: {e}")
            QMessageBox.critical(self, "Error", f"Could not move files: {str(e)}")

    def _get_desktop_window(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, 'desktop_icons'):
                return parent
            parent = parent.parent()
        return None


class TaskbarButton(QPushButton):
    """Styled taskbar button for window management"""

    def __init__(self, title: str, window=None, parent=None):
        super().__init__(title, parent)
        self.window_ref = window
        self.is_active = False
        self.is_minimized = False
        self.setFixedSize(180, 42)
        self.theme_mode = ThemeMode.DARK
        self._update_style()

    def _update_style(self):
        is_dark = self.theme_mode == ThemeMode.DARK
        base_style = """
            QPushButton {
                background: %(bg)s;
                color: %(text_color)s;
                border: %(border)s;
                border-radius: 6px;
                text-align: left;
                padding-left: 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover { background: %(hover_bg)s; }
            QPushButton:pressed { background: %(pressed_bg)s; }
        """
        if self.is_active:
            style_params = {
                'bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb)' if is_dark else 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4d648d, stop:1 #3a517d)',
                'text_color': 'white',
                'border': '1px solid #5a6fd8' if is_dark else '1px solid #3a517d',
                'hover_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6)' if is_dark else 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5d749d, stop:1 #4a618d)',
                'pressed_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #1e40af)' if is_dark else 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4d648d, stop:1 #3a517d)'
            }
        elif self.is_minimized:
            style_params = {
                'bg': 'rgba(102, 126, 234, 0.3)' if is_dark else 'rgba(77, 100, 141, 0.3)',
                'text_color': 'white' if is_dark else 'black',
                'border': '1px solid rgba(102, 126, 234, 0.5)' if is_dark else '1px solid rgba(77, 100, 141, 0.5)',
                'hover_bg': 'rgba(102, 126, 234, 0.5)' if is_dark else 'rgba(77, 100, 141, 0.5)',
                'pressed_bg': 'rgba(102, 126, 234, 0.4)' if is_dark else 'rgba(77, 100, 141, 0.4)'
            }
        else:
            bg_color = 'rgba(255, 255, 255, 0.08)' if is_dark else 'rgba(0, 0, 0, 0.05)'
            text_color = 'white' if is_dark else 'black'
            style_params = {
                'bg': bg_color,
                'text_color': text_color,
                'border': '1px solid rgba(255, 255, 255, 0.1)' if is_dark else '1px solid rgba(0, 0, 0, 0.1)',
                'hover_bg': 'rgba(255, 255, 255, 0.15)' if is_dark else 'rgba(0, 0, 0, 0.1)',
                'pressed_bg': 'rgba(255, 255, 255, 0.1)' if is_dark else 'rgba(0, 0, 0, 0.07)'
            }
        self.setStyleSheet(base_style % style_params)

    def set_active(self, active: bool):
        self.is_active = active
        self._update_style()

    def set_minimized(self, minimized: bool):
        self.is_minimized = minimized
        self._update_style()

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        self._update_style()


class Taskbar(QWidget):
    """Modern taskbar with start menu and clock"""
    start_clicked = Signal()
    clock_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_buttons = []
        self.theme_mode = ThemeMode.DARK
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        self.start_btn = QPushButton("⊞ Start")
        self.start_btn.setFixedSize(110, 46)
        self.start_btn.clicked.connect(lambda: self.start_clicked.emit())
        self.task_area = QHBoxLayout()
        self.task_area.setSpacing(6)
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setCursor(Qt.PointingHandCursor)
        self.clock_label.mousePressEvent = lambda e: self.clock_clicked.emit()
        layout.addWidget(self.start_btn)
        layout.addLayout(self.task_area)
        layout.addStretch()
        layout.addWidget(self.clock_label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self.timer.start(1000)
        self._update_time()
        self.apply_theme(ThemeMode.DARK)

    def _update_time(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%Y-%m-%d")
        self.clock_label.setText(f"{time_str}\n{date_str}")

    def apply_theme(self, theme_mode: ThemeMode, accent: str = None):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        accent = accent or getattr(self, "accent_color", "#3b82f6")
        self.accent_color = accent
        # Solidne tło paska (nie przezroczyste)
        bg = "#1e293b" if is_dark else "#e2e8f0"
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(bg))
        self.setPalette(pal)
        self.setStyleSheet(f"""
            Taskbar, QWidget#Taskbar {{
                background-color: {bg};
                border-top: 3px solid {accent};
            }}
        """)
        self.setObjectName("Taskbar")
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {accent}; opacity: 0.9; }}
            QPushButton:pressed {{ background-color: #1e3a5f; }}
        """)
        clock_text = "white" if is_dark else "#0f172a"
        clock_bg = "#334155" if is_dark else "#cbd5e1"
        self.clock_label.setStyleSheet(f"""
            color: {clock_text};
            font-weight: bold;
            font-size: 13px;
            padding: 8px 14px;
            background-color: {clock_bg};
            border-radius: 6px;
            min-width: 110px;
        """)
        for btn in self.task_buttons:
            btn.apply_theme(theme_mode)

    def add_task_button(self, title: str, window) -> TaskbarButton:
        btn = TaskbarButton(title[:20] + ("..." if len(title) > 20 else ""), window)
        btn.apply_theme(self.theme_mode)

        def on_button_click():
            # Klik = minimalizuj jeśli widoczne; przywróć jeśli zminimalizowane
            if window.is_minimized:
                window.toggle_minimize()
                window.bring_to_front()
            elif window.isVisible():
                window.toggle_minimize()
            else:
                window.setVisible(True)
                window.bring_to_front()

        btn.clicked.connect(on_button_click)
        self.task_area.addWidget(btn)
        self.task_buttons.append(btn)
        return btn

    def update_button_state(self, window, is_active=False, is_minimized=False):
        for btn in self.task_buttons:
            if btn.window_ref == window:
                btn.set_active(is_active)
                if is_minimized != btn.is_minimized:
                    btn.set_minimized(is_minimized)

    def remove_task_button(self, window):
        for btn in self.task_buttons[:]:
            if btn.window_ref == window:
                self.task_area.removeWidget(btn)
                btn.deleteLater()
                self.task_buttons.remove(btn)


class FileOperationThread(QThread):
    """Thread for handling file operations to prevent UI freezing"""
    operation_finished = Signal(str, bool, str)
    progress_updated = Signal(str, int)

    def __init__(self, operation_type: str, source: Union[str, Path],
                 destination: Union[str, Path], parent=None):
        super().__init__(parent)
        self.operation_type = operation_type
        self.source = Path(source)
        self.destination = Path(destination)
        self._cancel = False

    def run(self):
        try:
            if self.operation_type == "copy":
                if self.source.is_dir():
                    self._copy_directory(self.source, self.destination)
                else:
                    shutil.copy2(self.source, self.destination)
            elif self.operation_type == "move":
                if self.destination.exists():
                    if self.destination.is_dir():
                        shutil.rmtree(self.destination)
                    else:
                        self.destination.unlink()
                shutil.move(self.source, self.destination)
            elif self.operation_type == "delete":
                if self.source.is_dir():
                    shutil.rmtree(self.source)
                else:
                    self.source.unlink()
            self.operation_finished.emit(
                self.operation_type,
                True,
                f"Successfully {self.operation_type}d: {self.source.name}"
            )
        except Exception as e:
            logger.error(f"File operation error: {str(e)}")
            self.operation_finished.emit(
                self.operation_type,
                False,
                f"Error during {self.operation_type}: {str(e)}"
            )

    def _copy_directory(self, src: Path, dst: Path):
        if not dst.exists():
            dst.mkdir(parents=True, exist_ok=True)
        total_files = sum(1 for _ in src.rglob('*') if _.is_file())
        processed = 0
        for src_path in src.rglob('*'):
            rel_path = src_path.relative_to(src)
            dst_path = dst / rel_path
            if src_path.is_dir():
                dst_path.mkdir(parents=True, exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
            processed += 1
            if total_files > 0:
                progress = int((processed / total_files) * 100)
                self.progress_updated.emit("copy", progress)

    def cancel(self):
        self._cancel = True


def osmars_input_text(parent, title: str, label: str, text: str = "") -> tuple:
    """Okienko nazwy WEWNĄTRZ OSmars (nie natywny dialog OS)."""
    if not QT_AVAILABLE:
        return "", False
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.setMinimumWidth(360)
    dlg.setStyleSheet(
        "QDialog { background: #1e293b; color: white; }"
        "QLabel { color: #e2e8f0; font-size: 13px; }"
        "QLineEdit { background: #0f172a; color: white; border: 1px solid #475569; "
        "border-radius: 6px; padding: 8px; }"
        "QPushButton { background: #3b82f6; color: white; border: none; "
        "border-radius: 6px; padding: 8px 16px; font-weight: bold; }"
        "QPushButton#cancel { background: #475569; }"
    )
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel(label))
    edit = QLineEdit(text)
    edit.selectAll()
    lay.addWidget(edit)
    row = QHBoxLayout()
    ok_btn = QPushButton("OK")
    cancel_btn = QPushButton("Anuluj")
    cancel_btn.setObjectName("cancel")
    row.addStretch()
    row.addWidget(cancel_btn)
    row.addWidget(ok_btn)
    lay.addLayout(row)
    result = {"ok": False, "text": text}

    def accept():
        result["ok"] = True
        result["text"] = edit.text().strip()
        dlg.accept()

    ok_btn.clicked.connect(accept)
    cancel_btn.clicked.connect(dlg.reject)
    edit.returnPressed.connect(accept)
    dlg.exec()
    return result["text"], result["ok"]


def osmars_pick_file(parent, title: str, start_dir: str, patterns: str = "") -> tuple:
    """Wybór pliku WEWNĄTRZ OSmars (lista plików, nie natywny explorer OS)."""
    if not QT_AVAILABLE:
        return "", False
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setModal(True)
    dlg.resize(520, 400)
    dlg.setStyleSheet(
        "QDialog { background: #1e293b; color: white; }"
        "QLabel { color: #e2e8f0; }"
        "QListWidget { background: #0f172a; color: white; border: 1px solid #334155; "
        "border-radius: 6px; }"
        "QListWidget::item:selected { background: #3b82f6; }"
        "QPushButton { background: #3b82f6; color: white; border: none; "
        "border-radius: 6px; padding: 8px 16px; font-weight: bold; }"
        "QPushButton#cancel { background: #475569; }"
    )
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel(f"Katalog: {start_dir}"))
    lst = QListWidget()
    start = Path(start_dir)
    start.mkdir(parents=True, exist_ok=True)
    exts = []
    if "png" in patterns.lower() or "Images" in patterns or "Obrazy" in patterns:
        exts = [".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"]
    for p in sorted(start.iterdir() if start.exists() else []):
        if p.is_file():
            if not exts or p.suffix.lower() in exts:
                lst.addItem(p.name)
    lay.addWidget(lst, 1)
    # też przycisk „Inny katalog…” przez QFileDialog tylko jako fallback opcjonalny — Live: lista
    row = QHBoxLayout()
    ok_btn = QPushButton("Wybierz")
    cancel_btn = QPushButton("Anuluj")
    cancel_btn.setObjectName("cancel")
    browse_btn = QPushButton("Przeglądaj…")
    row.addWidget(browse_btn)
    row.addStretch()
    row.addWidget(cancel_btn)
    row.addWidget(ok_btn)
    lay.addLayout(row)
    result = {"path": "", "ok": False}

    def accept_sel():
        item = lst.currentItem()
        if item:
            result["path"] = str(start / item.text())
            result["ok"] = True
            dlg.accept()

    def browse():
        # W Live i tak wolimy wewnętrzny dialog; browse skanuje ten sam folder nadrzędny
        parent_dir = str(start.parent if start.parent.exists() else start)
        path, _ = QFileDialog.getOpenFileName(dlg, title, parent_dir, patterns or "All (*.*)")
        if path:
            result["path"] = path
            result["ok"] = True
            dlg.accept()

    ok_btn.clicked.connect(accept_sel)
    lst.itemDoubleClicked.connect(lambda _: accept_sel())
    cancel_btn.clicked.connect(dlg.reject)
    browse_btn.clicked.connect(browse)
    dlg.exec()
    return result["path"], result["ok"]


if QT_AVAILABLE:
    from PySide6.QtWidgets import QFileIconProvider as _QFileIconProvider

    class OsmarsFileIconProvider(_QFileIconProvider):
        """Ikony plików OSmars — .txt nie wygląda jak Python."""

        def icon(self, file_info):
            try:
                if hasattr(file_info, "isDir") and file_info.isDir():
                    return super().icon(file_info)
                name = ""
                if hasattr(file_info, "fileName"):
                    name = file_info.fileName().lower()
                elif hasattr(file_info, "filePath"):
                    name = str(file_info.filePath()).lower()
                if name.endswith((".py", ".pyw")):
                    return super().icon(file_info)
                if name.endswith((".mars", ".system")):
                    return self.style_icon(QStyle.SP_DriveNetIcon)
                if name.endswith((".txt", ".md", ".log", ".rtf", ".csv")):
                    return self.style_icon(QStyle.SP_FileIcon)
                if name.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
                    return self.style_icon(QStyle.SP_FileDialogContentsView)
                return super().icon(file_info)
            except Exception:
                return super().icon(file_info)

        def style_icon(self, sp):
            app = QApplication.instance()
            if app:
                return app.style().standardIcon(sp)
            return QIcon()


class FileExplorer(QWidget):
    """Modern file explorer with toolbar and status bar"""
    file_opened = Signal(Path)
    directory_changed = Signal(Path)

    def __init__(self, parent_os, start_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.parent_os = parent_os
        self.current_path = start_path or (parent_os.ROOT_DIR / "files")
        self.history = []
        self.history_index = -1
        self.operation_thread = None
        self.theme_mode = ThemeMode.DARK
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        splitter = QSplitter(Qt.Horizontal)
        self.model = QFileSystemModel()
        self.model.setRootPath(str(self.parent_os.ROOT_DIR))
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        if QT_AVAILABLE:
            try:
                self.model.setIconProvider(OsmarsFileIconProvider())
            except Exception:
                pass
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(self.parent_os.ROOT_DIR)))
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 120)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QTreeView.DragDrop)
        self.tree.setDefaultDropAction(Qt.CopyAction)
        self.tree.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree.doubleClicked.connect(self.open_item)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        # Drop z pulpitu (file:// paths)
        self.tree.viewport().setAcceptDrops(True)
        self.tree.dragEnterEvent = self._explorer_drag_enter
        self.tree.dragMoveEvent = self._explorer_drag_move
        self.tree.dropEvent = self._explorer_drop
        splitter.addWidget(self.tree)
        layout.addWidget(splitter, 1)
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_message("Ready")
        self.apply_theme(ThemeMode.DARK)

    def _explorer_drag_enter(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _explorer_drag_move(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def _explorer_drop(self, event):
        """Przyjmij pliki przeciągnięte z pulpitu / zewnątrz."""
        try:
            dest = self.current_path
            urls = event.mimeData().urls()
            paths = []
            if urls:
                paths = [Path(u.toLocalFile()) for u in urls if u.toLocalFile()]
            elif event.mimeData().hasText():
                t = event.mimeData().text().strip()
                if t:
                    paths = [Path(t)]
            for src in paths:
                if not src.exists():
                    continue
                target = dest / src.name
                if src.resolve() == target.resolve():
                    continue
                if src.is_dir():
                    shutil.copytree(str(src), str(target), dirs_exist_ok=True)
                else:
                    shutil.copy2(str(src), str(target))
            self.refresh()
            self.status_message(f"Skopiowano {len(paths)} element(ów)")
            event.acceptProposedAction()
        except Exception as e:
            self.status_message(f"Drop error: {e}")
            event.ignore()

    def _create_toolbar(self) -> QToolBar:
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        nav_icons = {'back': '◀', 'forward': '▶', 'up': '🔼', 'refresh': '🔄'}
        self.btn_back = self._create_toolbar_button(nav_icons['back'], "Back", self.go_back)
        self.btn_forward = self._create_toolbar_button(nav_icons['forward'], "Forward", self.go_forward)
        btn_up = self._create_toolbar_button(nav_icons['up'], "Up", self.go_up)
        btn_refresh = self._create_toolbar_button(nav_icons['refresh'], "Refresh", self.refresh)
        self.path_edit = QLineEdit(str(self.current_path))
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        btn_new_folder = self._create_toolbar_button("📁", "New Folder", self.create_folder)
        btn_new_file = self._create_toolbar_button("📄", "New File", self.create_file)
        toolbar.addWidget(self.btn_back)
        toolbar.addWidget(self.btn_forward)
        toolbar.addWidget(btn_up)
        toolbar.addWidget(btn_refresh)
        toolbar.addWidget(QLabel(" Path:"))
        toolbar.addWidget(self.path_edit)
        toolbar.addSeparator()
        toolbar.addWidget(btn_new_folder)
        toolbar.addWidget(btn_new_file)
        self.btn_back.setEnabled(False)
        self.btn_forward.setEnabled(False)
        return toolbar

    def _create_toolbar_button(self, text: str, tooltip: str, callback) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 28)
        btn.clicked.connect(callback)
        return btn

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "#2d2d30" if is_dark else "#ffffff"
        text_color = "white" if is_dark else "black"
        highlight_start = "#3b82f6" if is_dark else "#93c5fd"
        highlight_end = "#2563eb" if is_dark else "#60a5fa"
        toolbar_bg_start = "#f9f9f9" if is_dark else "#e0e0e0"
        toolbar_bg_end = "#f0f0f0" if is_dark else "#d0d0d0"
        toolbar_border_start = "#3b82f6" if is_dark else "#4d648d"
        toolbar_border_end = "#2563eb" if is_dark else "#3a517d"
        self.layout().itemAt(0).widget().setStyleSheet(f"""
            QToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {toolbar_bg_start}, stop:1 {toolbar_bg_end});
                border-bottom: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {toolbar_border_start}, stop:1 {toolbar_border_end});
                padding: 6px;
                spacing: 6px;
            }}
            QToolButton {{
                background-color: {"#3e3e42" if is_dark else "white"};
                border: 1px solid {"#555" if is_dark else "#d0d0d0"};
                border-radius: 4px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {highlight_start}, stop:1 {highlight_end});
                color: white;
                border-color: {highlight_start};
            }}
        """)
        tree_bg = "#1e1e1e" if is_dark else "#fafafa"
        tree_text = "white" if is_dark else "#1e1e1e"
        tree_hover = "#2a2a2a" if is_dark else "#e8f4ff"
        self.tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {tree_bg};
                color: {tree_text};
                border: none;
                font-size: 12px;
                outline: none;
            }}
            QTreeView::item {{ padding: 4px; border-radius: 4px; }}
            QTreeView::item:hover {{ background-color: {tree_hover}; }}
            QTreeView::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {highlight_start}, stop:1 {highlight_end});
                color: white;
            }}
        """)
        input_bg = "#2d2d30" if is_dark else "white"
        input_border = "#444444" if is_dark else "#d0d0d0"
        self.path_edit.setStyleSheet(f"""
            padding: 6px 10px;
            border: 1px solid {input_border};
            border-radius: 4px;
            font-size: 12px;
            background-color: {input_bg};
            color: {text_color};
        """)
        status_bg = "#1e1e1e" if is_dark else "#f9f9f9"
        status_border = "#444444" if is_dark else "#e0e0e0"
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {status_bg};
                border-top: 1px solid {status_border};
                color: {text_color};
                font-size: 10px;
                padding: 4px;
            }}
        """)

    def status_message(self, message: str):
        self.status_bar.showMessage(message, 3000)
        logger.info(f"Status: {message}")

    def navigate_to(self, path: Path, add_to_history: bool = True):
        try:
            path = path.resolve()
            if not path.exists():
                self.status_message(f"Path does not exist: {path}")
                return
            if not path.is_dir():
                self.status_message(f"Not a directory: {path}")
                return
            if not str(path).startswith(str(self.parent_os.ROOT_DIR)):
                self.status_message("Access denied: Cannot navigate outside OSmars root directory")
                return
            if add_to_history:
                if self.history_index < len(self.history) - 1:
                    self.history = self.history[:self.history_index + 1]
                if not self.history or self.history[-1] != path:
                    self.history.append(path)
                    self.history_index = len(self.history) - 1
            self.current_path = path
            self.refresh()
            self.btn_back.setEnabled(self.history_index > 0)
            self.btn_forward.setEnabled(self.history_index < len(self.history) - 1)
            self.directory_changed.emit(path)
        except Exception as e:
            logger.error(f"Navigation error: {str(e)}")
            self.status_message(f"Error navigating to path: {str(e)}")

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self.refresh()
            self.btn_back.setEnabled(self.history_index > 0)
            self.btn_forward.setEnabled(self.history_index < len(self.history) - 1)
            self.directory_changed.emit(self.current_path)

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self.refresh()
            self.btn_back.setEnabled(self.history_index > 0)
            self.btn_forward.setEnabled(self.history_index < len(self.history) - 1)
            self.directory_changed.emit(self.current_path)

    def refresh(self):
        try:
            self.path_edit.setText(str(self.current_path))
            self.tree.setRootIndex(self.model.index(str(self.current_path)))
            file_count = sum(1 for _ in self.current_path.iterdir() if _.is_file())
            dir_count = sum(1 for _ in self.current_path.iterdir() if _.is_dir())
            self.status_message(f"{dir_count} folders, {file_count} files")
        except Exception as e:
            logger.error(f"Refresh error: {str(e)}")
            self.status_message(f"Error refreshing view: {str(e)}")

    def go_up(self):
        parent = self.current_path.parent
        if parent >= self.parent_os.ROOT_DIR:
            self.navigate_to(parent)

    def navigate_to_path(self):
        path_text = self.path_edit.text().strip()
        if not path_text:
            return
        try:
            path = Path(path_text).resolve()
            self.navigate_to(path)
        except Exception as e:
            logger.error(f"Path navigation error: {str(e)}")
            QMessageBox.warning(self, "Invalid Path", f"Could not navigate to path:\n{str(e)}")
            self.path_edit.setText(str(self.current_path))

    def open_item(self, index):
        path = Path(self.model.filePath(index))
        try:
            if path.is_file():
                self.file_opened.emit(path)
            elif path.is_dir():
                self.navigate_to(path)
        except Exception as e:
            logger.error(f"Open item error: {str(e)}")
            self.status_message(f"Error opening item: {str(e)}")

    def show_context_menu(self, position):
        index = self.tree.indexAt(position)
        menu = QMenu()
        is_dark = self.theme_mode == ThemeMode.DARK
        text_color = "white" if is_dark else "black"
        bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
        hover_color = "#3b82f6" if is_dark else "#93c5fd"
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg_color};
                border: 1px solid {hover_color};
                border-radius: 6px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 20px;
                border-radius: 4px;
                color: {text_color};
                font-size: 12px;
            }}
            QMenu::item:selected {{ background-color: {hover_color}; }}
            QMenu::separator {{
                height: 1px;
                background: {"#444" if is_dark else "#ccc"};
                margin: 4px 8px;
            }}
        """)
        if index.isValid():
            path = Path(self.model.filePath(index))
            selected_paths = [Path(self.model.filePath(idx))
                              for idx in self.tree.selectionModel().selectedIndexes()
                              if idx.column() == 0]
            if len(selected_paths) == 1:
                menu.addAction("📂 Open", lambda: self.open_item(index))
                if path.suffix.lower() == '.py':
                    menu.addAction("▶️ Run", lambda: self.run_python_file(path))
                    menu.addAction("📝 Edit", lambda: self.edit_file(path))
                elif path.suffix.lower() == '.mars':
                    menu.addAction("▶️ Otwórz .mars", lambda p=path: self.file_opened.emit(p))
                elif path.suffix.lower() == '.system':
                    menu.addAction("🔧 Zastosuj .system", lambda p=path: self.file_opened.emit(p))
                elif path.suffix.lower() in ['.txt', '.md', '.log', '.json', '.xml', '.csv', '.ini']:
                    menu.addAction("📝 Edit", lambda: self.edit_file(path))
                menu.addSeparator()
                menu.addAction("✏️ Rename", lambda: self.rename_item(path))
            menu.addAction("🗑️ Delete", lambda: self.delete_items(selected_paths))
            menu.addSeparator()
            menu.addAction("📋 Copy", lambda: self.copy_items(selected_paths))
            menu.addAction("✂️ Cut", lambda: self.cut_items(selected_paths))
            menu.addAction("📋 Paste", lambda: self.paste_items())
            if len(selected_paths) == 1:
                menu.addSeparator()
                menu.addAction("ℹ️ Properties", lambda: self.show_properties(path))
        else:
            menu.addAction("📁 New Folder", self.create_folder)
            menu.addAction("📄 New File", self.create_file)
            menu.addSeparator()
            menu.addAction("📋 Paste", lambda: self.paste_items())
            menu.addSeparator()
            menu.addAction("🔄 Refresh", self.refresh)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def create_folder(self):
        name, ok = osmars_input_text(self, "Nowy folder", "Nazwa folderu:")
        if not ok or not name.strip():
            return
        folder_name = name.strip()
        new_path = self.current_path / folder_name
        try:
            if new_path.exists():
                raise FileExistsError(f"Folder '{folder_name}' already exists")
            new_path.mkdir(parents=True, exist_ok=False)
            self.refresh()
            self.status_message(f"Created folder: {folder_name}")
        except Exception as e:
            logger.error(f"Create folder error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not create folder:\n{str(e)}")

    def create_file(self):
        name, ok = osmars_input_text(self, "Nowy plik", "Nazwa pliku:")
        if not ok or not name.strip():
            return
        file_name = name.strip()
        new_path = self.current_path / file_name
        try:
            if new_path.exists():
                raise FileExistsError(f"File '{file_name}' already exists")
            new_path.touch(exist_ok=False)
            self.refresh()
            self.status_message(f"Created file: {file_name}")
        except Exception as e:
            logger.error(f"Create file error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not create file:\n{str(e)}")

    def rename_item(self, path: Path):
        old_name = path.name
        new_name, ok = osmars_input_text(self, "Zmień nazwę", "Nowa nazwa:", text=old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_path = path.parent / new_name.strip()
        try:
            if new_path.exists():
                raise FileExistsError(f"'{new_name}' already exists")
            path.rename(new_path)
            self.refresh()
            self.status_message(f"Renamed '{old_name}' to '{new_name}'")
        except Exception as e:
            logger.error(f"Rename error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not rename item:\n{str(e)}")

    def delete_items(self, paths: List[Path]):
        if not paths:
            return
        msg = f"Are you sure you want to delete {len(paths)} item(s)?\n"
        msg += "\n".join([f"- {p.name}" for p in paths[:5]])
        if len(paths) > 5:
            msg += f"\n- and {len(paths) - 5} more..."
        reply = QMessageBox.question(
            self, "Confirm Deletion", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        for path in paths:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except Exception as e:
                logger.error(f"Delete error for {path}: {str(e)}")
                QMessageBox.critical(self, "Error", f"Could not delete '{path.name}':\n{str(e)}")
                return
        self.refresh()
        self.status_message(f"Deleted {len(paths)} item(s)")

    def edit_file(self, path: Path):
        try:
            main_window = self._get_main_window()
            if hasattr(main_window, 'open_notepad'):
                main_window.open_notepad(str(path))
        except Exception as e:
            logger.error(f"Edit file error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not open editor:\n{str(e)}")

    def run_python_file(self, path: Path):
        try:
            main_window = self._get_main_window()
            if hasattr(main_window, 'run_python_script'):
                main_window.run_python_script(path)
        except Exception as e:
            logger.error(f"Run Python error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not run script:\n{str(e)}")

    def show_properties(self, path: Path):
        try:
            stat = path.stat()
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            size = stat.st_size if path.is_file() else self._get_dir_size(path)
            properties = (
                f"Name: {path.name}\n"
                f"Location: {path.parent}\n"
                f"Size: {self._format_size(size)}\n"
                f"Type: {'Directory' if path.is_dir() else f'File ({path.suffix})'}\n"
                f"Created: {created.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Permissions: {oct(stat.st_mode)[-3:]}"
            )
            QMessageBox.information(self, "Properties", properties)
        except Exception as e:
            logger.error(f"Properties error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not get properties:\n{str(e)}")

    def _get_dir_size(self, path: Path) -> int:
        total = 0
        try:
            for entry in path.rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception:
            pass
        return total

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def _get_main_window(self):
        window = self.window()
        while window.parent():
            window = window.parent().window()
        return window

    def copy_items(self, paths: List[Path]):
        if not paths:
            return
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(str(p)) for p in paths]
        mime_data.setUrls(urls)
        mime_data.setProperty("copy_operation", True)
        clipboard = QApplication.clipboard()
        clipboard.setMimeData(mime_data)
        self.status_message(f"Copied {len(paths)} item(s) to clipboard")

    def cut_items(self, paths: List[Path]):
        if not paths:
            return
        mime_data = QMimeData()
        urls = [QUrl.fromLocalFile(str(p)) for p in paths]
        mime_data.setUrls(urls)
        mime_data.setProperty("cut_operation", True)
        clipboard = QApplication.clipboard()
        clipboard.setMimeData(mime_data)
        self.status_message(f"Cut {len(paths)} item(s) to clipboard")

    def paste_items(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        if not mime_data.hasUrls():
            return
        urls = mime_data.urls()
        if not urls:
            return
        source_paths = [Path(url.toLocalFile()) for url in urls]
        is_cut_operation = mime_data.property("cut_operation")
        if is_cut_operation:
            reply = QMessageBox.question(
                self, "Move Items",
                f"Move {len(source_paths)} item(s) to this location?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                return
        self._perform_paste_operation(source_paths, is_cut_operation)

    def _perform_paste_operation(self, source_paths: List[Path], is_move: bool):
        dest_paths = []
        conflicts = []
        for src in source_paths:
            dest = self.current_path / src.name
            dest_paths.append(dest)
            if dest.exists():
                conflicts.append((src, dest))
        if conflicts:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("File Conflicts")
            dialog.setText(f"{len(conflicts)} file(s) already exist. What would you like to do?")
            skip_all_btn = dialog.addButton("Skip All", QMessageBox.RejectRole)
            replace_all_btn = dialog.addButton("Replace All", QMessageBox.AcceptRole)
            rename_all_btn = dialog.addButton("Rename All", QMessageBox.ActionRole)
            cancel_btn = dialog.addButton(QMessageBox.Cancel)
            dialog.exec()
            clicked_btn = dialog.clickedButton()
            if clicked_btn == cancel_btn:
                return
            elif clicked_btn == skip_all_btn:
                new_source_paths = []
                new_dest_paths = []
                for i, (src, dest) in enumerate(zip(source_paths, dest_paths)):
                    if dest not in [c[1] for c in conflicts]:
                        new_source_paths.append(src)
                        new_dest_paths.append(dest)
                source_paths = new_source_paths
                dest_paths = new_dest_paths
            elif clicked_btn == rename_all_btn:
                for i, (src, dest) in enumerate(conflicts):
                    base, ext = os.path.splitext(dest.name)
                    counter = 1
                    new_dest = dest.parent / f"{base} ({counter}){ext}"
                    while new_dest.exists():
                        counter += 1
                        new_dest = dest.parent / f"{base} ({counter}){ext}"
                    idx = dest_paths.index(dest)
                    dest_paths[idx] = new_dest
        try:
            for src, dest in zip(source_paths, dest_paths):
                if src.is_dir():
                    if is_move:
                        shutil.move(str(src), str(dest))
                    else:
                        self._copy_directory(src, dest)
                else:
                    if is_move:
                        shutil.move(str(src), str(dest))
                    else:
                        shutil.copy2(str(src), str(dest))
            self.refresh()
            operation = "Moved" if is_move else "Copied"
            self.status_message(f"{operation} {len(source_paths)} item(s)")
            if is_move:
                clipboard = QApplication.clipboard()
                clipboard.clear()
        except Exception as e:
            logger.error(f"Paste operation error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Paste operation failed:\n{str(e)}")

    def _copy_directory(self, src: Path, dst: Path):
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            s = item
            d = dst / item.name
            if s.is_dir():
                self._copy_directory(s, d)
            else:
                shutil.copy2(s, d)


class IntegratedTerminal(QWidget):
    """Integrated terminal with command history and syntax highlighting"""

    def __init__(self, parent_os, parent=None):
        super().__init__(parent)
        self.parent_os = parent_os
        self.command_history = []
        self.history_index = -1
        self.process = None
        self.theme_mode = ThemeMode.DARK
        self._setup_ui()
        self._print_banner()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 12)
        input_layout.setSpacing(8)
        self.prompt_label = QLabel(self._get_prompt())
        input_layout.addWidget(self.prompt_label)
        self.input_line = QLineEdit()
        self.input_line.returnPressed.connect(self.execute_command)
        self.input_line.installEventFilter(self)
        input_layout.addWidget(self.input_line, 1)
        layout.addWidget(input_container)
        self.apply_theme(ThemeMode.DARK)

    def eventFilter(self, obj, event):
        if obj == self.input_line and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self._history_up()
                return True
            elif event.key() == Qt.Key_Down:
                self._history_down()
                return True
        return super().eventFilter(obj, event)

    def _get_prompt(self) -> str:
        try:
            rel_path = os.path.relpath(
                str(self.parent_os.current_dir),
                str(self.parent_os.ROOT_DIR)
            )
            if rel_path == '.':
                rel_path = '~'
            return f"mars:{rel_path}$ "
        except Exception as e:
            logger.error(f"Prompt error: {str(e)}")
            return "mars:~$ "

    def _bin_dir(self) -> Path:
        d = self.parent_os.ROOT_DIR / "bin"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _print_banner(self):
        banner = """
╔════════════════════════════════════════╗
║         OSmars Terminal                ║
╠════════════════════════════════════════╣
║ Komendy = pliki z /bin (*.py)          ║
║ sudo <cmd>  — z uprawnieniami          ║
║ clear, help, cd, exit — wbudowane      ║
╚════════════════════════════════════════╝
"""
        self.output.appendPlainText(banner)

    def _append_output(self, text: str, color: str = "#d4d4d4"):
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        self.output.appendPlainText(clean_text)

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#d4d4d4" if is_dark else "#1e1e1e"
        input_bg = "#2d2d30" if is_dark else "#f9f9f9"
        input_border = "#3e3e42" if is_dark else "#cccccc"
        prompt_color = "#4ec9b0" if is_dark else "#007acc"
        selection_bg = "#264f78" if is_dark else "#add6ff"
        self.output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 12px;
                selection-background-color: {selection_bg};
            }}
        """)
        input_container = self.layout().itemAt(1).widget()
        input_container.setStyleSheet(f"background-color: {bg_color};")
        self.prompt_label.setStyleSheet(f"""
            QLabel {{
                color: {prompt_color};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                font-weight: bold;
            }}
        """)
        self.input_line.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {text_color};
                border: 1px solid {input_border};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {prompt_color}; }}
        """)

    def _history_up(self):
        if self.command_history and len(self.command_history) > 0:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.input_line.setText(self.command_history[-(self.history_index + 1)])
            elif self.history_index == -1:
                self.history_index = len(self.command_history) - 1
                self.input_line.setText(self.command_history[-(self.history_index + 1)])

    def _history_down(self):
        if self.history_index >= 0:
            self.history_index -= 1
            if self.history_index >= 0:
                self.input_line.setText(self.command_history[-(self.history_index + 1)])
            else:
                self.input_line.clear()

    def execute_command(self):
        command = self.input_line.text().strip()
        if not command:
            return
        if not self.command_history or self.command_history[-1] != command:
            self.command_history.append(command)
            self.history_index = -1
        self.output.appendPlainText(f"{self._get_prompt()}{command}")
        self.input_line.clear()
        try:
            parts = command.split()
            raw_cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            use_sudo = False
            if raw_cmd.lower() == "sudo":
                use_sudo = True
                if not args:
                    self._append_output("Użycie: sudo <komenda> [args...]")
                    self.prompt_label.setText(self._get_prompt())
                    return
                raw_cmd = args[0]
                args = args[1:]

            cmd = raw_cmd.lower()

            # Wbudowane (minimalne) + boot transakcje
            if cmd in ("clear", "cls"):
                self.output.clear()
            elif cmd == "help":
                self._show_help()
            elif cmd == "cd":
                self._handle_cd_command(args)
            elif cmd == "pwd":
                self._handle_pwd_command()
            elif cmd == "exit":
                self.window().close()
            elif cmd == "sync":
                if hasattr(self.parent_os, "boot_sync"):
                    self._call_parent_boot("boot_sync")
                else:
                    self._append_output("sync niedostępne (stary Recovery bez boot_sync)")
            elif cmd == "rollback":
                if hasattr(self.parent_os, "boot_rollback"):
                    self._call_parent_boot("boot_rollback")
                else:
                    self._append_output("rollback niedostępne")
            elif cmd == "status":
                if hasattr(self.parent_os, "cmd_status"):
                    self._call_parent_boot("cmd_status")
                else:
                    self._append_output(f"ROOT={self.parent_os.ROOT_DIR}")
            elif cmd == "from" and len(args) >= 2 and args[0].lower() == "mars" and args[1].lower() == "install":
                pkg = " ".join(args[2:]).strip()
                if hasattr(self.parent_os, "from_mars_install"):
                    self._call_parent_boot("from_mars_install", pkg)
                else:
                    self._append_output("from mars install niedostępne")
            else:
                # Szukaj w /bin: cmd.py albo cmd
                self._run_from_bin(raw_cmd, args, use_sudo=use_sudo)
        except Exception as e:
            self._append_output(f"Error: {str(e)}")
            logger.error(f"Command execution error: {str(e)}")
        self.prompt_label.setText(self._get_prompt())
        self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        )

    def _show_help(self):
        bin_dir = self._bin_dir()
        bins = sorted(p.stem for p in bin_dir.glob("*.py"))
        help_text = (
            "OSmars Terminal\n"
            "  Wbudowane: help, clear, cd, pwd, exit, sudo, sync, rollback, status\n  from mars install <pkg>  |  sync  |  rollback\n"
            "  Reszta: pliki z /bin/<nazwa>.py\n"
            f"  /bin: {', '.join(bins) if bins else '(pusto — dodaj *.py)'}\n"
            "  Przykład:  fastfetch   →  /bin/fastfetch.py\n"
            "             sudo update →  /bin/update.py (z sudo)\n"
        )
        self.output.appendPlainText(help_text)


    def _call_parent_boot(self, method_name: str, *args):
        """Wywołaj metodę Recovery (sync/rollback/status/install) i przechwyt stdout."""
        import io
        from contextlib import redirect_stdout, redirect_stderr
        fn = getattr(self.parent_os, method_name, None)
        if not callable(fn):
            self._append_output(f"Brak metody: {method_name}")
            return
        buf = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                fn(*args)
        except Exception as e:
            self._append_output(f"Error: {e}")
            return
        out = buf.getvalue().strip()
        errout = err.getvalue().strip()
        if out:
            self._append_output(out)
        if errout:
            self._append_output(errout)

    def _run_from_bin(self, cmd: str, args: list, use_sudo: bool = False):
        """Uruchom komendę jako /bin/<cmd>.py (plan OSmars)."""
        bin_dir = self._bin_dir()
        candidates = [
            bin_dir / f"{cmd}.py",
            bin_dir / cmd,
            bin_dir / f"{cmd.lower()}.py",
        ]
        script = next((p for p in candidates if p.is_file()), None)
        if not script:
            self._append_output(
                f"Nie znaleziono komendy '{cmd}' w /bin.\n"
                f"Dodaj plik: {bin_dir / (cmd + '.py')}"
            )
            return
        try:
            env = os.environ.copy()
            if use_sudo:
                env["OSMARS_SUDO"] = "1"
            result = subprocess.run(
                [sys.executable, str(script)] + list(args),
                cwd=str(self.parent_os.current_dir),
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            if result.stdout:
                self._append_output(result.stdout.rstrip())
            if result.stderr:
                self._append_output(result.stderr.rstrip())
            if result.returncode != 0 and not result.stdout and not result.stderr:
                self._append_output(f"(exit code {result.returncode})")
        except Exception as e:
            self._append_output(f"Błąd uruchamiania /bin/{cmd}: {e}")

    def _run_subprocess(self, command: str):
        try:
            result = subprocess.run(
                command, shell=True,
                cwd=str(self.parent_os.current_dir),
                capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                self._append_output(result.stdout)
            if result.stderr:
                self._append_output(f"Error: {result.stderr}")
            self._append_output(f"Exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            self._append_output("Command timed out after 30 seconds")
        except Exception as e:
            self._append_output(f"Error executing command: {str(e)}")

    def _handle_cd_command(self, args):
        if not args:
            self._append_output("Usage: cd <directory>")
            return
        target_dir = args[0]
        if target_dir == "..":
            new_dir = self.parent_os.current_dir.parent
        else:
            new_dir = self.parent_os.current_dir / target_dir
        try:
            new_dir = new_dir.resolve()
            if not new_dir.is_dir():
                self._append_output(f"Error: '{target_dir}' is not a directory")
                return
            if not str(new_dir).startswith(str(self.parent_os.ROOT_DIR)):
                self._append_output("Error: Cannot navigate outside OSmars root directory")
                return
            self.parent_os.current_dir = new_dir
            self._append_output(f"Changed directory to: {new_dir}")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _handle_ls_command(self, args):
        target_dir = self.parent_os.current_dir
        if args:
            target_dir = self.parent_os.current_dir / args[0]
        try:
            entries = sorted(target_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            output = []
            for entry in entries:
                if entry.name.startswith('.'):
                    continue
                if entry.is_dir():
                    output.append(f"{entry.name}/")
                elif entry.suffix.lower() in ['.py', '.pyw']:
                    output.append(f"{entry.name}")
                elif entry.suffix.lower() in ['.txt', '.md', '.log', '.json', '.xml']:
                    output.append(f"{entry.name}")
                else:
                    output.append(entry.name)
            if output:
                self._append_output("\n".join(output))
            else:
                self._append_output("(empty directory)")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _handle_pwd_command(self):
        self._append_output(str(self.parent_os.current_dir))

    def _handle_cat_command(self, args):
        if not args:
            self._append_output("Usage: cat <filename>")
            return
        file_path = self.parent_os.current_dir / args[0]
        try:
            if not file_path.exists():
                self._append_output(f"Error: File not found: {file_path.name}")
                return
            if file_path.is_dir():
                self._append_output(f"Error: '{file_path.name}' is a directory")
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if len(content) > 10000:
                content = content[:10000] + "\n... (output truncated due to size)"
            self._append_output(content)
        except UnicodeDecodeError:
            self._append_output(f"Warning: Binary file or encoding issue - showing hex dump")
            self._show_hex_dump(file_path)
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _show_hex_dump(self, file_path: Path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read(256)
            hex_dump = ""
            for i in range(0, len(data), 16):
                chunk = data[i:i + 16]
                hex_part = ' '.join(f"{b:02x}" for b in chunk)
                ascii_part = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                hex_dump += f"{i:04x}  {hex_part.ljust(47)}  {ascii_part}\n"
            if len(data) == 256:
                hex_dump += "... (file continues)\n"
            self._append_output(hex_dump)
        except Exception as e:
            self._append_output(f"Error creating hex dump: {str(e)}")

    def _handle_mkdir_command(self, args):
        if not args:
            self._append_output("Usage: mkdir <directory>")
            return
        dir_path = self.parent_os.current_dir / args[0]
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            self._append_output(f"Created directory: {dir_path.name}")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _handle_touch_command(self, args):
        if not args:
            self._append_output("Usage: touch <filename>")
            return
        file_path = self.parent_os.current_dir / args[0]
        try:
            file_path.touch(exist_ok=True)
            self._append_output(f"Created file: {file_path.name}")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _handle_rm_command(self, args):
        if not args:
            self._append_output("Usage: rm <filename>")
            return
        file_path = self.parent_os.current_dir / args[0]
        try:
            if not file_path.exists():
                self._append_output(f"Error: File not found: {file_path.name}")
                return
            if file_path.is_dir():
                self._append_output(f"Error: '{file_path.name}' is a directory. Use 'rmdir' instead.")
                return
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete file '{file_path.name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                file_path.unlink()
                self._append_output(f"Deleted file: {file_path.name}")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _handle_rmdir_command(self, args):
        if not args:
            self._append_output("Usage: rmdir <directory>")
            return
        dir_path = self.parent_os.current_dir / args[0]
        try:
            if not dir_path.exists():
                self._append_output(f"Error: Directory not found: {dir_path.name}")
                return
            if not dir_path.is_dir():
                self._append_output(f"Error: '{dir_path.name}' is not a directory")
                return
            if any(dir_path.iterdir()):
                self._append_output(f"Error: Directory '{dir_path.name}' is not empty")
                return
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Delete empty directory '{dir_path.name}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                dir_path.rmdir()
                self._append_output(f"Deleted directory: {dir_path.name}")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _handle_python_command(self, args):
        if not args:
            self._append_output("Usage: python <script.py>")
            return
        script_path = self.parent_os.current_dir / args[0]
        try:
            if not script_path.exists():
                self._append_output(f"Error: Script not found: {script_path.name}")
                return
            if not script_path.is_file():
                self._append_output(f"Error: '{script_path.name}' is not a file")
                return
            if script_path.suffix.lower() not in ['.py', '.pyw']:
                self._append_output(f"Error: '{script_path.name}' is not a Python script")
                return
            desktop_window = self._get_desktop_window()
            if hasattr(desktop_window, 'run_python_script'):
                desktop_window.run_python_script(script_path)
                self._append_output(f"Running script in separate window: {script_path.name}")
            else:
                self._run_subprocess(f"python \"{script_path}\"")
        except Exception as e:
            self._append_output(f"Error: {str(e)}")

    def _get_desktop_window(self):
        window = self.window()
        while window.parent():
            window = window.parent().window()
        return window


class BrowserWidget(QWidget):
    """Web browser with download support and fullscreen video"""

    def __init__(self, parent_os, url: str = "https://www.google.com", parent=None):
        super().__init__(parent)
        self.parent_os = parent_os
        self.is_video_fullscreen = False
        self.download_manager = None
        self.theme_mode = ThemeMode.DARK
        self.original_taskbar_state = True
        self._setup_ui(url)

    def _setup_ui(self, url: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.nav_bar = self._create_nav_bar(url)
        layout.addWidget(self.nav_bar)
        if self.parent_os.qt_webengine_available:
            self._setup_webengine(url, layout)
        else:
            self._show_webengine_error(url, layout)
        self.apply_theme(ThemeMode.DARK)

    def _create_nav_bar(self, url: str) -> QWidget:
        nav_bar = QWidget()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 6, 8, 6)
        nav_layout.setSpacing(6)
        self.btn_back = QPushButton("◀")
        self.btn_back.setFixedSize(30, 26)
        self.btn_back.setEnabled(False)
        self.btn_forward = QPushButton("▶")
        self.btn_forward.setFixedSize(30, 26)
        self.btn_forward.setEnabled(False)
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedSize(30, 26)
        self.url_bar = QLineEdit(url)
        btn_go = QPushButton("Go")
        btn_go.setFixedWidth(50)
        nav_layout.addWidget(self.btn_back)
        nav_layout.addWidget(self.btn_forward)
        nav_layout.addWidget(self.btn_refresh)
        nav_layout.addWidget(self.url_bar, 1)
        nav_layout.addWidget(btn_go)
        btn_go.clicked.connect(self._navigate_to_url)
        self.url_bar.returnPressed.connect(self._navigate_to_url)
        return nav_bar

    def _setup_webengine(self, initial_url: str, layout):
        if not QT_AVAILABLE or not hasattr(self.parent_os, 'qt_webengine_available'):
            self._show_webengine_error(initial_url, layout)
            return
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineDownloadRequest
            self.web_view = QWebEngineView()
            self.web_view.setUrl(QUrl(initial_url))
            profile = self.web_view.page().profile()
            downloads_dir = self.parent_os.ROOT_DIR / "files" / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            profile.setDownloadPath(str(downloads_dir))
            if hasattr(profile, 'downloadRequested'):
                profile.downloadRequested.connect(self._handle_download)
            settings = self.web_view.settings()
            if hasattr(settings, 'WebAttribute') and hasattr(settings.WebAttribute, 'FullScreenSupportEnabled'):
                settings.setAttribute(settings.WebAttribute.FullScreenSupportEnabled, True)
            self.web_view.page().fullScreenRequested.connect(self._handle_fullscreen_request)
            self.btn_back.clicked.connect(self.web_view.back)
            self.btn_forward.clicked.connect(self.web_view.forward)
            self.btn_refresh.clicked.connect(self.web_view.reload)
            self.web_view.urlChanged.connect(self._url_changed)
            self.web_view.loadStarted.connect(self._load_started)
            self.web_view.loadFinished.connect(self._load_finished)
            layout.addWidget(self.web_view, 1)
            self.status_bar = QStatusBar()
            layout.addWidget(self.status_bar)
            self.status_message("Ready")
        except ImportError as e:
            logger.error(f"WebEngine import error: {str(e)}")
            self._show_webengine_error(initial_url, layout)
        except Exception as e:
            logger.error(f"WebEngine setup error: {str(e)}")
            self._show_webengine_error(initial_url, layout)

    def _url_changed(self, url):
        self.url_bar.setText(url.toString())
        self.btn_back.setEnabled(self.web_view.history().canGoBack())
        self.btn_forward.setEnabled(self.web_view.history().canGoForward())

    def _load_started(self):
        self.btn_refresh.setText("❌")
        self.status_message("Loading page...")

    def _load_finished(self, success):
        self.btn_refresh.setText("🔄")
        if success:
            self.status_message(f"Loaded: {self.web_view.title()}")
        else:
            self.status_message("Error loading page")

    def _navigate_to_url(self):
        url_text = self.url_bar.text().strip()
        if not url_text:
            return
        if not url_text.startswith(('http://', 'https://', 'file://')):
            url_text = 'https://' + url_text
        try:
            url = QUrl(url_text)
            if url.isValid():
                self.web_view.setUrl(url)
            else:
                self.status_message("Invalid URL")
        except Exception as e:
            logger.error(f"URL navigation error: {str(e)}")
            self.status_message(f"Error: {str(e)}")

    def _show_webengine_error(self, url: str, layout):
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignCenter)
        error_layout.setContentsMargins(20, 20, 20, 20)
        error_label = QLabel(
            "⚠️ Wbudowana przeglądarka niedostępna\n"
            "Brak PySide6 WebEngine.\n"
            "Możesz otworzyć link w zewnętrznej przeglądarce systemu."
        )
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setWordWrap(True)
        open_btn = QPushButton("Otwórz w zewnętrznej przeglądarce")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        error_layout.addWidget(error_label)
        error_layout.addWidget(open_btn)
        layout.addWidget(error_widget)
        # NIE otwieraj automatycznie zewnętrznej przeglądarki – to powodowało wrażenie "drugiego GUI"

    def _handle_fullscreen_request(self, request):
        request.accept()
        self.is_video_fullscreen = request.toggleOn()
        desktop_window = self._get_desktop_window()
        if not desktop_window:
            return
        if self.is_video_fullscreen:
            self.nav_bar.hide()
            if hasattr(self, 'status_bar'):
                self.status_bar.hide()
            if hasattr(desktop_window, 'taskbar'):
                self.original_taskbar_state = desktop_window.taskbar.isVisible()
                desktop_window.taskbar.hide()
            self.original_geometry = self.window().geometry()
            screen = desktop_window.screen().availableGeometry()
            self.window().setGeometry(screen)
        else:
            self.nav_bar.show()
            if hasattr(self, 'status_bar'):
                self.status_bar.show()
            if hasattr(desktop_window, 'taskbar') and self.original_taskbar_state:
                desktop_window.taskbar.show()
            if hasattr(self, 'original_geometry'):
                self.window().setGeometry(self.original_geometry)

    def _get_desktop_window(self):
        window = self.window()
        while window.parent():
            parent = window.parent()
            if hasattr(parent, 'window') and callable(parent.window):
                window = parent.window()
            else:
                break
        return window

    def _handle_download(self, download):
        try:
            downloads_dir = self.parent_os.ROOT_DIR / "files" / "Downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            filename = download.downloadFileName()
            file_path = downloads_dir / filename
            counter = 1
            while file_path.exists():
                name, ext = os.path.splitext(filename)
                file_path = downloads_dir / f"{name} ({counter}){ext}"
                counter += 1
            download.setDownloadDirectory(str(downloads_dir))
            download.setDownloadFileName(file_path.name)
            if hasattr(download, 'isFinishedChanged'):
                download.isFinishedChanged.connect(lambda: self._download_finished(download))
            download.accept()
            self.status_message(f"Downloading: {filename}")
            logger.info(f"Download started: {filename}")
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            self.status_message(f"Download error: {str(e)}")

    def _download_finished(self, download):
        if download.isFinished():
            filename = download.downloadFileName()
            if hasattr(download, 'DownloadState') and hasattr(download.DownloadState,
                                                              'DownloadCompleted') and download.state() == download.DownloadState.DownloadCompleted:
                self.status_message(f"Download completed: {filename}")
                logger.info(f"Download completed: {filename}")
                QTimer.singleShot(2000, lambda: QMessageBox.information(
                    self, "Download Complete",
                    f"File saved to:\n{download.path()}"
                ))
            else:
                error_msg = download.errorString() or "Unknown error"
                self.status_message(f"Download failed: {error_msg}")
                logger.error(f"Download failed: {error_msg}")

    def status_message(self, message: str):
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message, 5000)

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "#2d2d30" if is_dark else "#ffffff"
        text_color = "white" if is_dark else "black"
        nav_bg_start = "#f9f9f9" if is_dark else "#e0e0e0"
        nav_bg_end = "#f0f0f0" if is_dark else "#d0d0d0"
        border_start = "#3b82f6" if is_dark else "#4d648d"
        border_end = "#2563eb" if is_dark else "#3a517d"
        input_bg = "#2d2d30" if is_dark else "white"
        input_border = "#444444" if is_dark else "#d0d0d0"
        btn_bg = "white" if is_dark else "#f0f0f0"
        btn_border = "#d0d0d0" if is_dark else "#cccccc"
        btn_hover_start = "#3b82f6" if is_dark else "#93c5fd"
        btn_hover_end = "#2563eb" if is_dark else "#60a5fa"
        status_bg = "#1e1e1e" if is_dark else "#f9f9f9"
        status_border = "#444444" if is_dark else "#e0e0e0"
        self.nav_bar.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {nav_bg_start}, stop:1 {nav_bg_end});
                border-bottom: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {border_start}, stop:1 {border_end});
            }}
        """)
        for btn in [self.btn_back, self.btn_forward, self.btn_refresh]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    border: 1px solid {btn_border};
                    border-radius: 4px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {btn_hover_start}, stop:1 {btn_hover_end});
                    color: white;
                    border-color: {btn_hover_start};
                }}
                QPushButton:disabled {{
                    background-color: {"#3e3e42" if is_dark else "#e0e0e0"};
                    color: {"#888" if is_dark else "#aaa"};
                    border-color: {"#555" if is_dark else "#d0d0d0"};
                }}
            """)
        self.url_bar.setStyleSheet(f"""
            QLineEdit {{
                padding: 6px 10px;
                border: 1px solid {input_border};
                border-radius: 4px;
                font-size: 12px;
                background-color: {input_bg};
                color: {text_color};
            }}
            QLineEdit:focus {{ border-color: {btn_hover_start}; }}
        """)
        if hasattr(self, 'status_bar'):
            self.status_bar.setStyleSheet(f"""
                QStatusBar {{
                    background: {status_bg};
                    border-top: 1px solid {status_border};
                    color: {text_color};
                    font-size: 10px;
                    padding: 4px;
                }}
            """)


class NotepadWidget(QWidget):
    """Advanced text editor with syntax highlighting and file operations"""

    def __init__(self, file_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.current_file = Path(file_path) if file_path else None
        self.is_modified = False
        self.theme_mode = ThemeMode.DARK
        self._setup_ui()
        if self.current_file:
            self._load_file(self.current_file)
        self.apply_theme(ThemeMode.DARK)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        self.editor = QPlainTextEdit()
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor, 1)
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_message("Ready")

    def _create_toolbar(self) -> QToolBar:
        toolbar = QToolBar()
        btn_new = QToolButton()
        btn_new.setText("📄 New")
        btn_new.clicked.connect(self.new_file)
        btn_open = QToolButton()
        btn_open.setText("📁 Open")
        btn_open.clicked.connect(self.open_file)
        btn_save = QToolButton()
        btn_save.setText("💾 Save")
        btn_save.clicked.connect(self.save_file)
        font_label = QLabel("Font:")
        font_size_spin = QSpinBox()
        font_size_spin.setRange(8, 48)
        font_size_spin.setValue(13)
        font_size_spin.setFixedWidth(50)
        font_size_spin.valueChanged.connect(self._change_font_size)
        toolbar.addWidget(btn_new)
        toolbar.addWidget(btn_open)
        toolbar.addWidget(btn_save)
        toolbar.addSeparator()
        toolbar.addWidget(font_label)
        toolbar.addWidget(font_size_spin)
        return toolbar

    def _change_font_size(self, size: int):
        font = self.editor.font()
        font.setPointSize(size)
        self.editor.setFont(font)

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "#2d2d30" if is_dark else "#ffffff"
        text_color = "white" if is_dark else "black"
        toolbar_bg_start = "#f9f9f9" if is_dark else "#e0e0e0"
        toolbar_bg_end = "#f0f0f0" if is_dark else "#d0d0d0"
        toolbar_border_start = "#3b82f6" if is_dark else "#4d648d"
        toolbar_border_end = "#2563eb" if is_dark else "#3a517d"
        editor_bg = "#1e1e1e" if is_dark else "#ffffff"
        editor_text = "#d4d4d4" if is_dark else "#1e1e1e"
        editor_border = "#3e3e42" if is_dark else "#e0e0e0"
        status_bg = "#1e1e1e" if is_dark else "#f9f9f9"
        status_border = "#444444" if is_dark else "#e0e0e0"
        btn_bg = "white" if is_dark else "#f0f0f0"
        btn_border = "#d0d0d0" if is_dark else "#cccccc"
        btn_hover_start = "#3b82f6" if is_dark else "#93c5fd"
        btn_hover_end = "#2563eb" if is_dark else "#60a5fa"
        self.layout().itemAt(0).widget().setStyleSheet(f"""
            QToolBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {toolbar_bg_start}, stop:1 {toolbar_bg_end});
                border-bottom: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {toolbar_border_start}, stop:1 {toolbar_border_end});
                padding: 6px;
                spacing: 8px;
            }}
            QToolButton {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {btn_hover_start}, stop:1 {btn_hover_end});
                color: white;
                border-color: {btn_hover_start};
            }}
            QLabel {{ color: {text_color}; }}
        """)
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {editor_bg};
                color: {editor_text};
                border: 1px solid {editor_border};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                padding: 16px;
                selection-background-color: {"#264f78" if is_dark else "#add6ff"};
            }}
        """)
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {status_bg};
                border-top: 1px solid {status_border};
                color: {text_color};
                font-size: 10px;
                padding: 4px;
            }}
        """)

    def _on_text_changed(self):
        self.is_modified = True
        text = self.editor.toPlainText()
        chars = len(text)
        lines = text.count('\n') + 1 if chars > 0 else 1
        file_info = Path(self.current_file).name if self.current_file else "Untitled"
        self.status_message(f"{file_info} | {chars} chars | {lines} lines | Modified")

    def status_message(self, message: str):
        self.status_bar.showMessage(message, 3000)

    def new_file(self):
        if self.is_modified:
            reply = QMessageBox.question(
                self, "Save Changes?",
                "Do you want to save changes to the current file?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        self.editor.clear()
        self.current_file = None
        self.is_modified = False
        self.status_message("New file created")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", str(Path.home()),
            "All Files (*.*);;Text Files (*.txt);;Python Files (*.py);;JSON Files (*.json)"
        )
        if file_path:
            self._load_file(Path(file_path))

    def _load_file(self, file_path: Path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.editor.setPlainText(content)
            self.current_file = file_path
            self.is_modified = False
            self.status_message(f"Opened: {file_path.name}")
            logger.info(f"File opened: {file_path}")
        except Exception as e:
            logger.error(f"File open error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")

    def save_file(self):
        if not self.current_file:
            self.save_file_as()
            return
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.is_modified = False
            self.status_message(f"Saved: {self.current_file.name}")
            logger.info(f"File saved: {self.current_file}")
        except Exception as e:
            logger.error(f"File save error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not save file:\n{str(e)}")

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", str(Path.home() / "untitled.txt"),
            "All Files (*.*);;Text Files (*.txt);;Python Files (*.py);;JSON Files (*.json)"
        )
        if file_path:
            self.current_file = Path(file_path)
            self.save_file()


class CalculatorWidget(QWidget):
    """Modern calculator with basic arithmetic operations"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_input = "0"
        self.current_operator = None
        self.first_number = 0
        self.waiting_for_input = True
        self.theme_mode = ThemeMode.DARK
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        self.display = QLineEdit("0")
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        main_layout.addWidget(self.display)
        buttons_grid = QGridLayout()
        buttons_grid.setSpacing(10)
        buttons = [
            ('C', 0, 0), ('CE', 0, 1), ('⌫', 0, 2), ('÷', 0, 3),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('×', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('-', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3),
            ('±', 4, 0), ('0', 4, 1), ('.', 4, 2), ('=', 4, 3)
        ]
        for text, row, col in buttons:
            btn = self._create_button(text)
            buttons_grid.addWidget(btn, row, col)
        main_layout.addLayout(buttons_grid)
        self.apply_theme(ThemeMode.DARK)

    def _create_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(80, 60)
        btn.clicked.connect(lambda: self._button_clicked(text))
        return btn

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        is_dark = theme_mode == ThemeMode.DARK
        bg_color = "#2d2d30" if is_dark else "#ffffff"
        text_color = "white" if is_dark else "black"
        display_bg = "#1e1e1e" if is_dark else "#f5f5f5"
        display_text = "white" if is_dark else "#1e1e1e"
        display_border_start = "#3b82f6" if is_dark else "#4d648d"
        display_border_end = "#2563eb" if is_dark else "#3a517d"
        number_bg = "#3e3e42" if is_dark else "#e0e0e0"
        number_hover = "#4e4e52" if is_dark else "#d0d0d0"
        operator_bg_start = "#3b82f6" if is_dark else "#93c5fd"
        operator_bg_end = "#2563eb" if is_dark else "#60a5fa"
        operator_hover_start = "#60a5fa" if is_dark else "#93c5fd"
        operator_hover_end = "#3b82f6" if is_dark else "#60a5fa"
        function_bg = "#3e3e42" if is_dark else "#e0e0e0"
        function_hover = "#4e4e52" if is_dark else "#d0d0d0"
        self.setStyleSheet(f"background-color: {bg_color};")
        self.display.setStyleSheet(f"""
            QLineEdit {{
                background-color: {display_bg};
                color: {display_text};
                border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {display_border_start}, stop:1 {display_border_end});
                border-radius: 10px;
                padding: 20px;
                font-size: 32px;
                font-weight: bold;
            }}
        """)
        for i in range(self.layout().itemAt(1).layout().count()):
            btn = self.layout().itemAt(1).layout().itemAt(i).widget()
            text = btn.text()
            if text in '0123456789.':
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {number_bg};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 20px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {number_hover}; }}
                """)
            elif text in '+-×÷=':
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 {operator_bg_start}, stop:1 {operator_bg_end});
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 22px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 {operator_hover_start}, stop:1 {operator_hover_end});
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {function_bg};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 16px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: {function_hover}; }}
                """)

    def _button_clicked(self, text: str):
        if text in '0123456789':
            self._handle_digit(text)
        elif text == '.':
            self._handle_decimal()
        elif text in '+-×÷':
            self._handle_operator(text)
        elif text == '=':
            self._calculate_result()
        elif text == 'C':
            self._clear_all()
        elif text == 'CE':
            self._clear_entry()
        elif text == '⌫':
            self._backspace()
        elif text == '±':
            self._toggle_sign()

    def _handle_digit(self, digit: str):
        if self.waiting_for_input or self.current_input == "0":
            self.current_input = digit
        else:
            self.current_input += digit
        self._update_display()
        self.waiting_for_input = False

    def _handle_decimal(self):
        if self.waiting_for_input:
            self.current_input = "0."
        elif '.' not in self.current_input:
            self.current_input += "."
        self._update_display()
        self.waiting_for_input = False

    def _handle_operator(self, operator: str):
        if not self.waiting_for_input:
            self._calculate_result()
        self.first_number = float(self.current_input)
        self.current_operator = operator
        self.waiting_for_input = True

    def _calculate_result(self):
        if self.current_operator is None:
            return
        second_number = float(self.current_input)
        result = 0
        try:
            if self.current_operator == '+':
                result = self.first_number + second_number
            elif self.current_operator == '-':
                result = self.first_number - second_number
            elif self.current_operator == '×':
                result = self.first_number * second_number
            elif self.current_operator == '÷':
                if second_number == 0:
                    self.current_input = "Error"
                    self._update_display()
                    return
                result = self.first_number / second_number
            if result.is_integer():
                self.current_input = str(int(result))
            else:
                self.current_input = f"{result:.10f}".rstrip('0').rstrip('.')
        except Exception as e:
            logger.error(f"Calculation error: {str(e)}")
            self.current_input = "Error"
        self.current_operator = None
        self._update_display()
        self.waiting_for_input = True

    def _clear_all(self):
        self.current_input = "0"
        self.current_operator = None
        self.first_number = 0
        self.waiting_for_input = True
        self._update_display()

    def _clear_entry(self):
        self.current_input = "0"
        self._update_display()
        self.waiting_for_input = False

    def _backspace(self):
        if self.waiting_for_input:
            return
        if len(self.current_input) > 1:
            self.current_input = self.current_input[:-1]
        else:
            self.current_input = "0"
        self._update_display()

    def _toggle_sign(self):
        if self.current_input == "0" or self.current_input == "Error":
            return
        if self.current_input.startswith('-'):
            self.current_input = self.current_input[1:]
        else:
            self.current_input = '-' + self.current_input
        self._update_display()

    def _update_display(self):
        try:
            if self.current_input not in ["0", "Error"]:
                num = float(self.current_input)
                if num.is_integer():
                    display_text = f"{int(num):,}"
                else:
                    display_text = self.current_input
            else:
                display_text = self.current_input
        except ValueError:
            display_text = self.current_input
        self.display.setText(display_text)


class DesktopWindow(QMainWindow):
    """Main desktop window with window management and desktop icons"""

    def __init__(self, parent_os):
        super().__init__()
        self.parent_os = parent_os
        self.windows = []
        self.desktop_icons = []
        self.icon_positions = {}
        self.wallpaper_path = None
        self.theme_mode = ThemeMode.DARK
        self.original_taskbar_state = True
        if not hasattr(parent_os, 'window_manager'):
            parent_os.window_manager = WindowManager(self)
        self._load_settings()
        self._setup_ui()
        self._apply_theme()
        self._create_desktop_icons()
        QTimer.singleShot(100, self.update_icon_visibility)
        QTimer.singleShot(100, self._show_fullscreen)
        QTimer.singleShot(200, self.refresh_desktop)

    def _load_settings(self):
        settings_file = self.parent_os.ROOT_DIR / "system" / "desktop_settings.json"
        self.accent_color = "#3b82f6"
        try:
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.icon_positions = settings.get('icon_positions', {})
                self.wallpaper_path = settings.get('wallpaper', None)
                theme_str = settings.get('theme_mode', 'dark')
                self.theme_mode = ThemeMode(theme_str) if theme_str in ThemeMode._value2member_map_ else ThemeMode.DARK
                self.accent_color = settings.get('accent_color', "#3b82f6")
            else:
                self.icon_positions = {}
                self.wallpaper_path = None
                self.theme_mode = ThemeMode.DARK
            logger.info("Desktop settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading desktop settings: {str(e)}")
            self.icon_positions = {}
            self.wallpaper_path = None
            self.theme_mode = ThemeMode.DARK

    def _save_settings(self):
        settings_file = self.parent_os.ROOT_DIR / "system" / "desktop_settings.json"
        try:
            settings = {
                'icon_positions': self.icon_positions,
                'wallpaper': self.wallpaper_path,
                'theme_mode': self.theme_mode.value,
                'accent_color': getattr(self, 'accent_color', '#3b82f6'),
            }
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            logger.info("Desktop settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving desktop settings: {str(e)}")

    def _setup_ui(self):
        self.setWindowTitle("OSmars Desktop")
        self.setAttribute(Qt.WA_TranslucentBackground)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ScrollArea — da się przewijać wszystkie ikony
        self.desktop_scroll = QScrollArea()
        self.desktop_scroll.setWidgetResizable(True)
        self.desktop_scroll.setFrameShape(QFrame.NoFrame)
        self.desktop_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.desktop_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.desktop_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 10px; background: #1e293b; }"
            "QScrollBar::handle:vertical { background: #475569; border-radius: 4px; }"
        )

        self.desktop_area = QWidget()
        self.desktop_area.setMinimumSize(1200, 900)  # większy obszar na ikony
        self.desktop_area.setStyleSheet("background: transparent;")
        self._update_wallpaper()
        self.desktop_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.desktop_area.customContextMenuRequested.connect(self._show_desktop_context_menu)
        self.desktop_area.setAcceptDrops(True)
        self.desktop_area.dragEnterEvent = self._desktop_drag_enter
        self.desktop_area.dropEvent = self._desktop_drop_event
        self.window_container = QWidget(self.desktop_area)
        self.window_container.setStyleSheet("background: transparent;")
        self.window_container.setGeometry(self.desktop_area.rect())
        self.window_container.lower()
        desktop_layout = QVBoxLayout(self.desktop_area)
        desktop_layout.setContentsMargins(0, 0, 0, 0)

        self.desktop_scroll.setWidget(self.desktop_area)
        main_layout.addWidget(self.desktop_scroll, 1)

        self.taskbar = Taskbar()
        self.taskbar.start_clicked.connect(self._open_start_menu)
        self.taskbar.clock_clicked.connect(self._show_clock_info)
        main_layout.addWidget(self.taskbar)
        self.apply_theme(self.theme_mode)

    def apply_theme(self, theme_mode: ThemeMode):
        self.theme_mode = theme_mode
        accent = getattr(self, "accent_color", "#3b82f6")
        self.taskbar.apply_theme(theme_mode, accent=accent)
        for window in self.windows:
            if hasattr(window, 'apply_theme'):
                window.apply_theme(theme_mode)
            # Title bar accent
            if hasattr(window, 'title_bar') and window.title_bar is not None:
                window.title_bar.setStyleSheet(
                    f"background-color: {accent}; color: white;"
                )
        for icon in self.desktop_icons:
            icon.apply_theme(theme_mode)

    def _show_fullscreen(self):
        screen_rect = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen_rect)
        self.showFullScreen()

    def _update_wallpaper(self):
        if self.wallpaper_path and Path(self.wallpaper_path).exists():
            self.desktop_area.setStyleSheet(f"""
                QWidget {{
                    background-image: url("{self.wallpaper_path}");
                    background-position: center;
                    background-repeat: no-repeat;
                    background-size: cover;
                }}
            """)
        else:
            self.desktop_area.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0f172a, stop:1 #1e293b);
                }
            """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'window_container'):
            self.window_container.setGeometry(self.desktop_area.rect())
        QTimer.singleShot(100, self.update_icon_visibility)

    def _create_desktop_icons(self):
        default_icons = [
            ("This PC", "💻", None, DesktopIconType.SYSTEM),
            ("Browser", "🌐", None, DesktopIconType.APPLICATION),
            ("Terminal", "⌨️", None, DesktopIconType.APPLICATION),
            ("Notepad", "📝", None, DesktopIconType.APPLICATION),
            ("Calculator", "🧮", None, DesktopIconType.APPLICATION),
            ("Downloads", "📥", None, DesktopIconType.FOLDER),
        ]
        for name, icon, path, icon_type in default_icons:
            self._add_desktop_icon(name, icon, path, icon_type)
        self._load_desktop_files()

    def _load_desktop_files(self):
        desktop_dir = self.parent_os.ROOT_DIR / "files" / "Desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        try:
            for item in desktop_dir.iterdir():
                if item.name.startswith('.') or item.name == "desktop.ini":
                    continue
                icon_text = self._get_file_icon(item)
                icon_type = DesktopIconType.FOLDER if item.is_dir() else DesktopIconType.FILE
                pixmap = None
                display_name = item.name
                if item.is_file() and item.suffix.lower() == ".mars":
                    icon_type = DesktopIconType.APPLICATION
                    meta = self._mars_read_meta(item)
                    if meta.get("name"):
                        display_name = meta["name"]
                    pixmap = self._mars_load_icon_pixmap(item, meta)
                    if pixmap is None:
                        icon_text = "🪐"
                elif item.is_file() and item.suffix.lower() == ".system":
                    icon_type = DesktopIconType.APPLICATION
                    meta = self._system_read_meta(item)
                    if meta.get("name"):
                        display_name = meta["name"]
                    icon_text = "🔧"
                self._add_desktop_icon(display_name, icon_text, str(item), icon_type, icon_pixmap=pixmap)
            logger.info(f"Loaded desktop files from {desktop_dir}")
        except Exception as e:
            logger.error(f"Error loading desktop files: {str(e)}")

    def _get_file_icon(self, path: Path) -> str:
        if path.is_dir():
            return "📁"
        ext = path.suffix.lower()
        icon_map = {
            '.txt': '📄', '.md': '📄', '.log': '📄', '.rtf': '📄',
            '.pdf': '📕', '.doc': '📘', '.docx': '📘', '.odt': '📘',
            '.py': '🐍', '.pyw': '🐍',
            '.js': '📜', '.html': '🌐', '.css': '🎨',
            '.json': '🧾', '.xml': '🧾', '.yaml': '🧾', '.yml': '🧾',
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️', '.svg': '🖼️',
            '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.ogg': '🎵',
            '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
            '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦', '.gz': '📦',
            '.exe': '⚙️', '.msi': '⚙️', '.bat': '⚙️', '.sh': '⚙️',
            '.ini': '⚙️', '.cfg': '⚙️', '.conf': '⚙️',
            '.mars': '🪐',
            '.system': '🔧',
        }
        return icon_map.get(ext, '📄')

    def _add_desktop_icon(self, name: str, icon_text: str, path: Optional[str] = None,
                          icon_type: DesktopIconType = DesktopIconType.FILE,
                          icon_pixmap: Optional[QPixmap] = None) -> DesktopIcon:
        self.setAttribute(Qt.WA_TranslucentBackground)
        for icon in self.desktop_icons:
            if icon.name == name and icon.path == (path or ""):
                return icon
        icon = DesktopIcon(name, icon_text, path, icon_type, self.desktop_area, icon_pixmap=icon_pixmap)
        icon.setAttribute(Qt.WA_TranslucentBackground)
        icon.setWindowFlags(icon.windowFlags() | Qt.FramelessWindowHint)
        icon.setStyleSheet("background: transparent;")
        icon.apply_theme(self.theme_mode)
        if name in self.icon_positions:
            pos = self.icon_positions[name]
            target_pos = QPoint(int(pos.get("x", DesktopIcon.MARGIN)), int(pos.get("y", DesktopIcon.MARGIN)))
            target_pos = icon.snap_to_grid(target_pos)
            if icon.is_position_occupied(target_pos):
                target_pos = icon.find_free_position(target_pos)
            icon.move(target_pos)
        else:
            # układ: kolumna w dół, potem następna kolumna (nie ukos!)
            target_pos = icon.find_free_position(QPoint(DesktopIcon.MARGIN, DesktopIcon.MARGIN))
            icon.move(target_pos)
        self.icon_positions[name] = {"x": target_pos.x(), "y": target_pos.y()}
        icon.double_clicked.connect(self._handle_icon_double_click)
        icon.position_changed.connect(self._save_icon_positions)
        icon.show()
        icon.raise_()
        self.desktop_icons.append(icon)
        return icon

    def _save_icon_positions(self):
        for icon in self.desktop_icons:
            self.icon_positions[icon.name] = {'x': icon.x(), 'y': icon.y()}
        self._save_settings()

    def refresh_desktop(self):
        for icon in self.desktop_icons:
            icon.deleteLater()
        self.desktop_icons.clear()
        self._create_desktop_icons()
        for icon in self.desktop_icons:
            icon.raise_()
        self.update_icon_visibility()

    def _handle_icon_double_click(self, name: str, path: str):
        handlers = {
            "This PC": self.open_file_explorer,
            "Browser": lambda: self.open_browser("https://www.google.com"),
            "Terminal": self.open_terminal,
            "Notepad": self.open_notepad,
            "Calculator": self.open_calculator,
            "Downloads": self.open_downloads,
        }
        if name in handlers:
            handlers[name]()
        elif path:
            self._open_desktop_file(path)

    def show_icon_context_menu(self, icon: DesktopIcon, position):
        menu = QMenu(self)
        is_dark = self.theme_mode == ThemeMode.DARK
        text_color = "white" if is_dark else "black"
        bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
        hover_color = "#3b82f6" if is_dark else "#93c5fd"
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg_color};
                border: 1px solid {hover_color};
                border-radius: 6px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 16px;
                border-radius: 4px;
                color: {text_color};
                font-size: 12px;
            }}
            QMenu::item:selected {{ background-color: {hover_color}; }}
            QMenu::separator {{
                height: 1px;
                background: {"#444" if is_dark else "#ccc"};
                margin: 4px 8px;
            }}
        """)
        if icon.path:
            path = Path(icon.path)
            if path.exists():
                if path.suffix.lower() == '.mars':
                    menu.addAction("▶️ Uruchom", lambda p=path: self._mars_run(p))
                    menu.addAction("📂 Rozpakuj tutaj", lambda p=path: self._mars_unpack(p))
                    menu.addAction("📥 Zainstaluj (apps + boot/sync)", lambda p=path: self._mars_install(p, queue_boot=False))
                    menu.addAction("🔧 Kolejka do boot (instrukcja)", lambda p=path: self._mars_install(p, queue_boot=True))
                    menu.addSeparator()
                    menu.addAction("ℹ️ Info .mars", lambda p=path: self._mars_show_info(p))
                    menu.addSeparator()
                elif path.suffix.lower() == '.system':
                    menu.addAction("🔧 Zastosuj przez boot/sync", lambda p=path: self._system_apply(p, do_sync=True))
                    menu.addAction("📋 Tylko kolejka boot", lambda p=path: self._system_apply(p, do_sync=False))
                    menu.addAction("📂 Rozpakuj tutaj", lambda p=path: self._mars_unpack(p))
                    menu.addSeparator()
                    menu.addAction("ℹ️ Info .system", lambda p=path: self._system_show_info(p))
                    menu.addSeparator()
                elif path.suffix.lower() == '.py':
                    menu.addAction("▶️ Run", lambda: self.run_python_script(path))
                    menu.addAction("📝 Edit", lambda: self.open_notepad(str(path)))
                    menu.addSeparator()
                elif path.suffix.lower() in ['.txt', '.md', '.log', '.json', '.xml', '.csv']:
                    menu.addAction("📝 Edit", lambda: self.open_notepad(str(path)))
                    menu.addSeparator()
                elif path.is_dir():
                    menu.addAction("📂 Open", lambda: self.open_file_explorer_at(path))
                    menu.addSeparator()
                menu.addAction("✏️ Rename", lambda: self._rename_desktop_item(icon))
                menu.addAction("🗑️ Delete", lambda: self._delete_desktop_item(icon))
                menu.addSeparator()
                menu.addAction("ℹ️ Properties", lambda: self._show_file_properties(path))
                menu.exec(position)

    def _rename_desktop_item(self, icon: DesktopIcon):
        # uses osmars_input_text below
        if not icon.path or not Path(icon.path).exists():
            return
        path = Path(icon.path)
        new_name, ok = osmars_input_text(self, "Zmień nazwę", "Nowa nazwa:", text=path.name)
        if ok and new_name.strip() and new_name.strip() != path.name:
            try:
                new_path = path.parent / new_name.strip()
                if new_path.exists():
                    QMessageBox.warning(self, "Error", f"'{new_name}' already exists")
                    return
                path.rename(new_path)
                icon.name = new_name
                icon.path = str(new_path)
                if path.is_file():
                    icon.findChild(QLabel).setText(self._get_file_icon(new_path))
                self.refresh_desktop()
                logger.info(f"Renamed '{path.name}' to '{new_name}'")
            except Exception as e:
                logger.error(f"Rename error: {str(e)}")
                QMessageBox.critical(self, "Error", f"Could not rename item:\n{str(e)}")

    def _delete_desktop_item(self, icon: DesktopIcon):
        if not icon.path or not Path(icon.path).exists():
            return
        path = Path(icon.path)
        item_type = "folder" if path.is_dir() else "file"
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete this {item_type}?\n{path.name}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self.desktop_icons.remove(icon)
                if icon.name in self.icon_positions:
                    del self.icon_positions[icon.name]
                icon.deleteLater()
                self._save_settings()
                logger.info(f"Deleted {item_type}: {path.name}")
            except Exception as e:
                logger.error(f"Delete error: {str(e)}")
                QMessageBox.critical(self, "Error", f"Could not delete item:\n{str(e)}")

    def _show_file_properties(self, path: Path):
        try:
            stat = path.stat()
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            if path.is_dir():
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                item_type = "Directory"
            else:
                size = stat.st_size
                item_type = f"File ({path.suffix})" if path.suffix else "File"
            properties = (
                f"Name: {path.name}\n"
                f"Location: {path.parent}\n"
                f"Size: {self._format_size(size)}\n"
                f"Type: {item_type}\n"
                f"Created: {created.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Permissions: {oct(stat.st_mode)[-3:]}"
            )
            QMessageBox.information(self, "Properties", properties)
        except Exception as e:
            logger.error(f"Properties error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not get properties:\n{str(e)}")

    def _format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def _show_desktop_context_menu(self, position):
        menu = QMenu(self)
        is_dark = self.theme_mode == ThemeMode.DARK
        text_color = "white" if is_dark else "black"
        bg_color = "#2b2b2b" if is_dark else "#f0f0f0"
        hover_color = "#3b82f6" if is_dark else "#93c5fd"
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {bg_color};
                border: 1px solid {hover_color};
                border-radius: 6px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 8px 30px 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                color: {text_color};
            }}
            QMenu::item:selected {{ background-color: {hover_color}; }}
            QMenu::separator {{
                height: 1px;
                background: {"#444" if is_dark else "#ccc"};
                margin: 4px 8px;
            }}
        """)
        new_menu = menu.addMenu("📄 New")
        new_menu.setStyleSheet(menu.styleSheet())
        new_menu.addAction("📝 Text Document", self._create_desktop_text_file)
        new_menu.addAction("🐍 Python Script", self._create_desktop_python_file)
        new_menu.addAction("📁 Folder", self._create_desktop_folder)
        menu.addSeparator()
        menu.addAction("🔄 Refresh Desktop", self.refresh_desktop)
        menu.addSeparator()
        view_menu = menu.addMenu("👁️ View")
        view_menu.setStyleSheet(menu.styleSheet())
        view_menu.addAction("🖼️ Change Wallpaper", self._change_wallpaper)
        view_menu.addAction("🌓 Toggle Theme", self._toggle_theme)
        view_menu.addAction("🔄 Reset Icon Positions", self._reset_icon_positions)
        menu.exec(self.desktop_area.mapToGlobal(position))

    def _create_desktop_text_file(self):
        name, ok = osmars_input_text(self, "Nowy plik tekstowy", "Nazwa pliku:")
        if not ok or not name.strip():
            return
        file_name = name.strip()
        if not file_name.endswith(('.txt', '.md')):
            file_name += '.txt'
        desktop_dir = self.parent_os.ROOT_DIR / "files" / "Desktop"
        file_path = desktop_dir / file_name
        try:
            file_path.touch(exist_ok=False)
            self.refresh_desktop()
            logger.info(f"Created text file: {file_name}")
        except FileExistsError:
            QMessageBox.warning(self, "Error", f"File '{file_name}' already exists")
        except Exception as e:
            logger.error(f"Create text file error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not create file:\n{str(e)}")

    def _create_desktop_python_file(self):
        name, ok = osmars_input_text(self, "Nowy plik Python", "Nazwa pliku:")
        if not ok or not name.strip():
            return
        file_name = name.strip()
        if not file_name.endswith('.py'):
            file_name += '.py'
        desktop_dir = self.parent_os.ROOT_DIR / "files" / "Desktop"
        file_path = desktop_dir / file_name
        template = f"""#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
{file_name}
Created on {datetime.datetime.now().strftime('%Y-%m-%d')}
\"\"\"
def main():
    print("Hello from {file_name}!")

if __name__ == "__main__":
    main()
"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(template)
            self.refresh_desktop()
            logger.info(f"Created Python file: {file_name}")
        except FileExistsError:
            QMessageBox.warning(self, "Error", f"File '{file_name}' already exists")
        except Exception as e:
            logger.error(f"Create Python file error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not create file:\n{str(e)}")

    def _create_desktop_folder(self):
        name, ok = osmars_input_text(self, "Nowy folder", "Nazwa folderu:")
        if not ok or not name.strip():
            return
        folder_name = name.strip()
        desktop_dir = self.parent_os.ROOT_DIR / "files" / "Desktop"
        folder_path = desktop_dir / folder_name
        try:
            folder_path.mkdir(parents=True, exist_ok=False)
            self.refresh_desktop()
            logger.info(f"Created folder: {folder_name}")
        except FileExistsError:
            QMessageBox.warning(self, "Error", f"Folder '{folder_name}' already exists")
        except Exception as e:
            logger.error(f"Create folder error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not create folder:\n{str(e)}")

    def _change_wallpaper(self):
        """Wybór tapety w oknie OSmars (Live — bez natywnego OS dialogu jako głównego)."""
        wallpapers_dir = self.parent_os.ROOT_DIR / "files" / "wallpapers"
        wallpapers_dir.mkdir(parents=True, exist_ok=True)
        file_path, ok = osmars_pick_file(
            self,
            "Wybierz tapetę",
            str(wallpapers_dir),
            "Obrazy (*.png *.jpg *.jpeg *.bmp *.webp);;Wszystkie pliki (*.*)"
        )
        if ok and file_path:
            self.wallpaper_path = file_path
            self._update_wallpaper()
            self._save_settings()
            logger.info(f"Wallpaper changed to: {file_path}")
            QMessageBox.information(self, "Tapeta", f"Ustawiono:\n{file_path}")

    def _toggle_theme(self):
        self.theme_mode = ThemeMode.LIGHT if self.theme_mode == ThemeMode.DARK else ThemeMode.DARK
        self._apply_theme()
        self._save_settings()
        theme_name = "Light" if self.theme_mode == ThemeMode.LIGHT else "Dark"
        QMessageBox.information(
            self, "Theme Changed",
            f"Switched to {theme_name} mode.\nAll windows and components have been updated."
        )

    def _apply_theme(self):
        is_dark = self.theme_mode == ThemeMode.DARK
        palette = QPalette()
        bg_color = QColor("#2d2d30" if is_dark else "#ffffff")
        text_color = QColor("white" if is_dark else "black")
        palette.setColor(QPalette.Window, bg_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, QColor("#1e1e1e" if is_dark else "#f9f9f9"))
        palette.setColor(QPalette.AlternateBase, bg_color)
        palette.setColor(QPalette.ToolTipBase, QColor("#1e1e1e" if is_dark else "#f9f9f9"))
        palette.setColor(QPalette.ToolTipText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, bg_color)
        palette.setColor(QPalette.ButtonText, text_color)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor("#4a90e2"))
        palette.setColor(QPalette.Highlight, QColor("#3b82f6" if is_dark else "#93c5fd"))
        palette.setColor(QPalette.HighlightedText, Qt.black if is_dark else Qt.white)
        QApplication.setPalette(palette)
        self.apply_theme(self.theme_mode)

    def _reset_icon_positions(self):
        reply = QMessageBox.question(
            self, "Reset Positions",
            "Reset all desktop icon positions to default?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.icon_positions = {}
            self._save_settings()
            self.refresh_desktop()

    def _desktop_drag_enter(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _desktop_drop_event(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        desktop_dir = self.parent_os.ROOT_DIR / "files" / "Desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        try:
            for url in urls:
                source_path = Path(url.toLocalFile())
                if not source_path.exists():
                    continue
                if source_path.parent == desktop_dir:
                    for icon in self.desktop_icons:
                        if icon.path == str(source_path):
                            drop_pos = event.position().toPoint()
                            snapped_pos = icon.snap_to_grid(drop_pos)
                            final_pos = icon.find_free_position(snapped_pos)
                            icon.move(final_pos)
                            self._save_icon_positions()
                            break
                    continue
                dest_path = desktop_dir / source_path.name
                counter = 1
                while dest_path.exists():
                    name, ext = os.path.splitext(source_path.name)
                    dest_path = desktop_dir / f"{name} ({counter}){ext}"
                    counter += 1
                if event.modifiers() & Qt.ControlModifier:
                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)
                    action = "copied"
                else:
                    shutil.move(source_path, dest_path)
                    action = "moved"
                logger.info(f"File {action} to desktop: {dest_path.name}")
                event.acceptProposedAction()
                self.refresh_desktop()
        except Exception as e:
            logger.error(f"Drop operation error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not move/copy files:\n{str(e)}")

    def create_window(self, title: str, content_widget: QWidget,
                      app_type: Optional[ApplicationType] = None) -> ManagedWindow:
        window = ManagedWindow(title, content_widget, self.window_container)
        window.apply_theme(self.theme_mode)
        window.closed.connect(lambda w: self._remove_window(w))
        window.minimized_changed.connect(lambda w, m: self._window_state_changed(w, m))
        window.maximized_changed.connect(lambda w, m: self.update_icon_visibility())
        offset = len([w for w in self.windows if not w.is_minimized]) * 35
        max_offset = 200
        offset = min(offset, max_offset)
        window.move(60 + offset, 60 + offset)
        task_btn = self.taskbar.add_task_button(title, window)
        window.task_button = task_btn
        window.show()
        window.raise_()
        self.windows.append(window)
        window.installEventFilter(WindowEventFilter(self))
        self.update_icon_visibility()
        return window

    def _remove_window(self, window: ManagedWindow):
        if window in self.windows:
            self.windows.remove(window)
        if hasattr(window, 'task_button') and window.task_button:
            self.taskbar.remove_task_button(window)
        self.update_icon_visibility()

    def _window_state_changed(self, window: ManagedWindow, is_minimized: bool):
        if hasattr(window, 'task_button'):
            self.taskbar.update_button_state(window, is_active=False, is_minimized=is_minimized)
        self.update_icon_visibility()

    def update_icon_visibility(self):
        has_maximized = any(w.is_maximized and w.isVisible() and not w.is_minimized for w in self.windows)
        for icon in self.desktop_icons:
            if has_maximized:
                icon.setVisible(False)
                continue
            icon_rect = icon.geometry()
            is_covered = False
            for window in self.windows:
                if not window.is_minimized and window.isVisible():
                    window_rect = window.geometry()
                    if window_rect.intersects(icon_rect):
                        is_covered = True
                        break
            icon.setVisible(not is_covered)

    def status_message(self, message: str):
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message, 3000)

    def open_file_explorer(self):
        explorer = FileExplorer(self.parent_os)
        explorer.apply_theme(self.theme_mode)
        explorer.file_opened.connect(lambda p: self._open_desktop_file(str(p)))
        self.create_window("File Explorer", explorer, ApplicationType.FILE_EXPLORER)

    def open_file_explorer_at(self, path: Path):
        explorer = FileExplorer(self.parent_os, path)
        explorer.apply_theme(self.theme_mode)
        explorer.file_opened.connect(lambda p: self._open_desktop_file(str(p)))
        title = f"File Explorer - {path.name}"
        self.create_window(title, explorer, ApplicationType.FILE_EXPLORER)

    def open_browser(self, url: str = "https://www.google.com"):
        browser = BrowserWidget(self.parent_os, url)
        browser.apply_theme(self.theme_mode)
        self.create_window("Web Browser", browser, ApplicationType.BROWSER)

    def open_terminal(self):
        terminal = IntegratedTerminal(self.parent_os)
        terminal.apply_theme(self.theme_mode)
        self.create_window("Terminal", terminal, ApplicationType.TERMINAL)

    def open_notepad(self, file_path: Optional[str] = None):
        notepad = NotepadWidget(file_path)
        notepad.apply_theme(self.theme_mode)
        title = f"Notepad - {Path(file_path).name}" if file_path else "Notepad"
        self.create_window(title, notepad, ApplicationType.NOTEPAD)

    def open_calculator(self):
        calculator = CalculatorWidget()
        calculator.apply_theme(self.theme_mode)
        window = self.create_window("Calculator", calculator, ApplicationType.CALCULATOR)
        window.resize(350, 450)

    def open_downloads(self):
        downloads_dir = self.parent_os.ROOT_DIR / "files" / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        explorer = FileExplorer(self.parent_os, downloads_dir)
        explorer.apply_theme(self.theme_mode)
        explorer.file_opened.connect(lambda p: self._open_desktop_file(str(p)))
        self.create_window("Downloads", explorer, ApplicationType.DOWNLOADS)


    # ---------------- .mars on desktop ----------------
    def _mars_cache_dir(self) -> Path:
        d = self.parent_os.ROOT_DIR / "temp" / "mars_icons"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _mars_read_meta(self, mars_path: Path) -> dict:
        """Odczyt mars.json / manifest.json z archiwum .mars"""
        import zipfile
        try:
            with zipfile.ZipFile(mars_path, "r") as zf:
                for cand in ("mars.json", "manifest.json"):
                    if cand in zf.namelist():
                        return json.loads(zf.read(cand).decode("utf-8"))
        except Exception as e:
            logger.error(f"mars meta read error: {e}")
        return {}

    def _mars_load_icon_pixmap(self, mars_path: Path, meta: Optional[dict] = None) -> Optional[QPixmap]:
        """Wyciągnij ikonę z .mars do temp i zwróć QPixmap."""
        import zipfile
        meta = meta or self._mars_read_meta(mars_path)
        icon_name = meta.get("icon")
        if not icon_name:
            return None
        try:
            with zipfile.ZipFile(mars_path, "r") as zf:
                # icon może być "icon.png" lub zagnieżdżona ścieżka
                names = zf.namelist()
                match = None
                if icon_name in names:
                    match = icon_name
                else:
                    for n in names:
                        if n.endswith("/" + icon_name) or n.endswith(icon_name):
                            match = n
                            break
                if not match:
                    return None
                data = zf.read(match)
            cache = self._mars_cache_dir() / f"{mars_path.stem}_{Path(match).name}"
            cache.write_bytes(data)
            pm = QPixmap(str(cache))
            return pm if not pm.isNull() else None
        except Exception as e:
            logger.error(f"mars icon load error: {e}")
            return None

    def _mars_extract_entry_to_temp(self, mars_path: Path, entry: str) -> Optional[Path]:
        import zipfile
        try:
            with zipfile.ZipFile(mars_path, "r") as zf:
                if entry not in zf.namelist():
                    # spróbuj bez folderu
                    for n in zf.namelist():
                        if n.endswith("/" + entry) or n == entry:
                            entry = n
                            break
                    else:
                        return None
                dest_dir = self.parent_os.ROOT_DIR / "temp" / "mars_run" / mars_path.stem
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                zf.extractall(dest_dir)
                return dest_dir / entry
        except Exception as e:
            logger.error(f"mars extract entry: {e}")
            return None

    def _mars_run(self, mars_path: Path):
        """
        Dwuklik / Uruchom:
        - type=app (domyślnie) → uruchom entry (main.py)
        - type=installer → instalacja do apps (+ sync)
        - type=system → tylko kolejka do boot (bez natychmiastowego run)
        """
        meta = self._mars_read_meta(mars_path)
        mtype = (meta.get("type") or "app").lower()
        name = meta.get("name") or mars_path.stem
        entry = meta.get("entry") or "main.py"

        if mtype in ("installer", "install"):
            reply = QMessageBox.question(
                self, "Instalator .mars",
                f"'{name}' to instalator.\nZainstalować teraz (apps + sync)?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._mars_install(mars_path, queue_boot=False)
            return

        if mtype in ("system", "boot", "update"):
            reply = QMessageBox.question(
                self, "Paczka systemowa",
                f"'{name}' wymaga boot/instrukcji (podmiana plików systemowych).\n"
                f"Dodać do kolejki boot i uruchomić sync?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self._mars_install(mars_path, queue_boot=True)
            return

        # app — uruchom entry
        entry_path = self._mars_extract_entry_to_temp(mars_path, entry)
        if not entry_path or not entry_path.exists():
            QMessageBox.warning(self, ".mars", f"Brak entry '{entry}' w {mars_path.name}")
            return
        if entry_path.suffix.lower() in (".py", ".pyw"):
            self.run_python_script(entry_path)
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(entry_path)))

    def _mars_unpack(self, mars_path: Path):
        """Rozpakuj .mars obok pliku na pulpicie / w katalogu pliku."""
        import zipfile
        dest = mars_path.parent / mars_path.stem
        try:
            if dest.exists():
                reply = QMessageBox.question(
                    self, "Rozpakuj",
                    f"Folder '{dest.name}' już istnieje. Nadpisać?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(mars_path, "r") as zf:
                zf.extractall(dest)
            QMessageBox.information(self, "Rozpakowano", f"Wypakowano do:\n{dest}")
            self.refresh_desktop()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", str(e))

    def _mars_install(self, mars_path: Path, queue_boot: bool = False):
        """
        Instalacja .mars:
        - kopiuje do boot/updates
        - buduje instrukcja.json (stage)
        - opcjonalnie od razu sync (gdy queue_boot=False i parent ma boot_sync)
        - zapis ver/<id>.json
        """
        try:
            updates = self.parent_os.ROOT_DIR / "boot" / "updates"
            updates.mkdir(parents=True, exist_ok=True)
            dest = updates / mars_path.name
            shutil.copy2(mars_path, dest)

            if hasattr(self.parent_os, "_stage_mars_transaction"):
                instr = self.parent_os._stage_mars_transaction(dest, mars_path.stem)
                pkg_id = instr.get("package") or mars_path.stem
                # ver JSON (plan: nazwa + wersja do update)
                self._mars_write_ver_json(pkg_id, instr)
                msg = (
                    f"Paczka '{pkg_id}' przygotowana w boot/instrukcja.json.\n"
                    f"ID transakcji: {instr.get('id')}\n"
                )
                if queue_boot:
                    msg += "\nUżyj 'sync' w terminalu / Recovery, albo restart (auto_sync_on_boot)."
                    QMessageBox.information(self, "Kolejka boot", msg)
                else:
                    if hasattr(self.parent_os, "boot_sync"):
                        ok = self.parent_os.boot_sync()
                        if ok:
                            QMessageBox.information(
                                self, "Zainstalowano",
                                f"{msg}\nsync: OK → apps/{pkg_id}/"
                            )
                        else:
                            QMessageBox.warning(self, "Instalacja", f"{msg}\nsync: BŁĄD — zobacz status / rollback")
                    else:
                        QMessageBox.information(self, "Instalacja", msg + "\nBrak boot_sync — uruchom Recovery → sync")
            else:
                QMessageBox.warning(self, "Instalacja", "Recovery bez _stage_mars_transaction — skopiowano tylko do boot/updates")
            self.refresh_desktop()
        except Exception as e:
            logger.error(f"mars install error: {e}")
            QMessageBox.critical(self, "Błąd instalacji", str(e))

    def _mars_write_ver_json(self, pkg_id: str, instr_or_meta: dict):
        """ver/<id>.json — nazwa + wersja (do późniejszego update)."""
        ver_dir = self.parent_os.ROOT_DIR / "ver"
        ver_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "id": pkg_id,
            "name": instr_or_meta.get("name") or pkg_id,
            "version": str(instr_or_meta.get("version") or "0.0.0"),
            "type": instr_or_meta.get("action") or instr_or_meta.get("type") or "app",
            "updated_at": datetime.datetime.now().isoformat(),
        }
        (ver_dir / f"{pkg_id}.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        # kompatybilność ze starym write_ver txt
        (ver_dir / f"{pkg_id}.txt").write_text(data["version"] + "\n", encoding="utf-8")

    def _mars_show_info(self, mars_path: Path):
        meta = self._mars_read_meta(mars_path)
        if not meta:
            QMessageBox.warning(self, ".mars", "Brak mars.json w paczce")
            return
        text = (
            f"Name:    {meta.get('name', '?')}\n"
            f"ID:      {meta.get('id', '?')}\n"
            f"Version: {meta.get('version', '?')}\n"
            f"Type:    {meta.get('type', 'app')}\n"
            f"Entry:   {meta.get('entry', 'main.py')}\n"
            f"Icon:    {meta.get('icon', '(brak)')}\n"
            f"Desc:    {meta.get('description', '')}\n"
            f"\nFile: {mars_path}"
        )
        QMessageBox.information(self, f"Info — {mars_path.name}", text)



    def _system_read_meta(self, path: Path) -> dict:
        import zipfile
        try:
            with zipfile.ZipFile(path, "r") as zf:
                if "system.json" in zf.namelist():
                    return json.loads(zf.read("system.json").decode("utf-8"))
        except Exception as e:
            logger.error(f"system meta: {e}")
        return {}

    def _system_show_info(self, path: Path):
        meta = self._system_read_meta(path)
        if not meta:
            QMessageBox.warning(self, ".system", "Brak system.json")
            return
        targets = meta.get("targets") or []
        lines = "\n".join(f"  {t.get('from')} → {t.get('to')}" for t in targets)
        QMessageBox.information(
            self, f"Info — {path.name}",
            f"Name: {meta.get('name')}\nID: {meta.get('id')}\nVersion: {meta.get('version')}\n"
            f"Type: system\nTargets:\n{lines}\n\nFile: {path}"
        )

    def _system_apply(self, path: Path, do_sync: bool = True):
        """Wrzuć .system do boot i opcjonalnie sync."""
        try:
            updates = self.parent_os.ROOT_DIR / "boot" / "updates"
            downloads = self.parent_os.ROOT_DIR / "files" / "Downloads"
            updates.mkdir(parents=True, exist_ok=True)
            downloads.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, downloads / path.name)
            dest = updates / path.name
            shutil.copy2(path, dest)
            if not hasattr(self.parent_os, "_stage_system_transaction"):
                QMessageBox.warning(self, ".system", "Recovery bez _stage_system_transaction")
                return
            instr = self.parent_os._stage_system_transaction(dest, path.stem)
            self._mars_write_ver_json(instr.get("package") or path.stem, instr)
            msg = f"Kolejka boot: {instr.get('id')}\n{instr.get('name')} v{instr.get('version')}"
            if do_sync and hasattr(self.parent_os, "boot_sync"):
                ok = self.parent_os.boot_sync()
                if ok:
                    QMessageBox.information(self, ".system", msg + "\n\nsync: OK")
                else:
                    QMessageBox.warning(self, ".system", msg + "\n\nsync: BŁĄD — status / rollback")
            else:
                QMessageBox.information(self, ".system", msg + "\n\nUruchom: sync")
            self.refresh_desktop()
        except Exception as e:
            logger.error(f"system apply: {e}")
            QMessageBox.critical(self, "Błąd .system", str(e))

    def _open_desktop_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            QMessageBox.warning(self, "Error", f"File not found: {path.name}")
            return
        try:
            if path.suffix.lower() == '.mars':
                self._mars_run(path)
            elif path.suffix.lower() == '.system':
                self._system_apply(path, do_sync=True)
            elif path.suffix.lower() == '.py':
                self.run_python_script(path)
            elif path.suffix.lower() in ['.txt', '.md', '.log', '.json', '.xml', '.csv', '.ini']:
                self.open_notepad(str(path))
            elif path.is_dir():
                self.open_file_explorer_at(path)
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as e:
            logger.error(f"Open file error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not open file:\n{str(e)}")

    def run_python_script(self, script_path: Path):
        if not script_path.exists():
            QMessageBox.critical(self, "Error", f"Script not found:\n{script_path}")
            return
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        output = QPlainTextEdit()
        output.setReadOnly(True)
        layout.addWidget(output, 1)
        status_bar = QStatusBar()
        layout.addWidget(status_bar)
        title = f"Python - {script_path.name}"
        window = self.create_window(title, container, ApplicationType.TERMINAL)
        window.apply_theme(self.theme_mode)
        is_dark = self.theme_mode == ThemeMode.DARK
        output_bg = "#1e1e1e" if is_dark else "#ffffff"
        output_text = "#d4d4d4" if is_dark else "#1e1e1e"
        output.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {output_bg};
                color: {output_text};
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 12px;
                selection-background-color: {"#264f78" if is_dark else "#add6ff"};
            }}
        """)
        status_bg = "#1e1e1e" if is_dark else "#f9f9f9"
        status_text = "#4ec9b0" if is_dark else "#007acc"
        status_border = "#3b82f6" if is_dark else "#93c5fd"
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {status_bg};
                color: {status_text};
                border-top: 1px solid {status_border};
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 4px;
            }}
        """)

        def execute_script():
            try:
                status_bar.showMessage("Executing script...")
                output.appendPlainText(f"Running: {script_path.name}")
                output.appendPlainText("=" * 60)
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True, text=True,
                    cwd=str(script_path.parent), timeout=30
                )
                if result.stdout:
                    output.appendPlainText(result.stdout)
                if result.stderr:
                    output.appendPlainText("\n⚠️ Errors:")
                    output.appendPlainText(result.stderr)
                output.appendPlainText("\n" + "=" * 60)
                status_text = f"✓ Completed with exit code {result.returncode}" if result.returncode == 0 else f"✗ Completed with errors (code: {result.returncode})"
                status_bar.showMessage(status_text)
            except subprocess.TimeoutExpired:
                output.appendPlainText("\n⚠️ Error: Script execution timed out after 30 seconds")
                status_bar.showMessage("✗ Timeout error")
            except Exception as e:
                output.appendPlainText(f"\n⚠️ Error: {str(e)}")
                status_bar.showMessage(f"✗ Execution error: {str(e)}")

        QTimer.singleShot(100, execute_script)

    def _open_start_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                border: 2px solid #3b82f6;
                border-radius: 8px;
                padding: 12px;
            }
            QMenu::item {
                padding: 10px 40px 10px 20px;
                border-radius: 6px;
                font-size: 13px;
                color: white;
                font-weight: 500;
            }
            QMenu::item:selected { background-color: #3b82f6; }
            QMenu::separator { height: 1px; background: #444; margin: 6px 0; }
        """)
        menu.addAction("📁 File Explorer", self.open_file_explorer)
        menu.addAction("🌐 Web Browser", lambda: self.open_browser("https://www.google.com"))
        menu.addAction("⌨️ Terminal", self.open_terminal)
        menu.addAction("📝 Notepad", self.open_notepad)
        menu.addAction("🧮 Calculator", self.open_calculator)
        menu.addSeparator()
        settings_menu = menu.addMenu("⚙️ Settings")
        settings_menu.setStyleSheet(menu.styleSheet())
        settings_menu.addAction("🎨 Display Settings", self._open_display_settings)
        settings_menu.addAction("ℹ️ System Information", self._show_system_info)
        menu.addSeparator()
        menu.addAction("💾 Install OSmars to Disk", self._open_installer)
        menu.addSeparator()
        menu.addAction("🔄 Restart", self._restart_system)
        menu.addAction("🔌 Shutdown", self.close)
        menu_height = menu.sizeHint().height()
        menu_pos = self.taskbar.mapToGlobal(QPoint(10, -menu_height - 10))
        menu.exec(menu_pos)

    def _show_clock_info(self):
        current_time = datetime.datetime.now()
        info = (
            f"Current Date and Time\n"
            f"Date: {current_time.strftime('%A, %B %d, %Y')}\n"
            f"Time: {current_time.strftime('%H:%M:%S')}\n"
            f"System Uptime: {self._get_uptime()}"
        )
        QMessageBox.information(self, "System Time", info)

    def _get_uptime(self) -> str:
        try:
            start_time = datetime.datetime.now() - datetime.timedelta(hours=2, minutes=45)
            uptime = datetime.datetime.now() - start_time
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{uptime.days} days, {hours} hours, {minutes} minutes"
        except:
            return "Unknown"

    def _open_display_settings(self):
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        title = QLabel("🎨 Display Settings")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #3b82f6;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        wallpaper_group = QGroupBox("🖼️ Wallpaper")
        wallpaper_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3b82f6;
                border-radius: 6px;
                margin-top: 1ex;
                font-weight: bold;
                color: #3b82f6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        wallpaper_layout = QVBoxLayout(wallpaper_group)
        wallpaper_layout.setContentsMargins(15, 15, 15, 15)
        wallpaper_layout.setSpacing(10)
        current_wallpaper = QLabel(
            self.wallpaper_path if self.wallpaper_path else "Default gradient"
        )
        current_wallpaper.setStyleSheet("color: #aaa; font-size: 11px;")
        current_wallpaper.setWordWrap(True)
        wallpaper_layout.addWidget(current_wallpaper)
        btn_change = QPushButton("📁 Browse")
        btn_change.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #60a5fa, stop:1 #3b82f6);
            }
        """)
        btn_change.clicked.connect(lambda: [
            self._change_wallpaper(),
            current_wallpaper.setText(
                self.wallpaper_path if self.wallpaper_path else "Default gradient"
            )
        ])
        wallpaper_layout.addWidget(btn_change)
        btn_reset = QPushButton("🔄 Reset to Default")
        btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #3e3e42;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #4e4e52; }
        """)
        btn_reset.clicked.connect(lambda: [
            setattr(self, 'wallpaper_path', None),
            self._update_wallpaper(),
            self._save_settings(),
            current_wallpaper.setText("Default gradient")
        ])
        wallpaper_layout.addWidget(btn_reset)
        layout.addWidget(wallpaper_group)
        theme_group = QGroupBox("🌓 Theme Mode")
        theme_group.setStyleSheet(wallpaper_group.styleSheet())
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setContentsMargins(15, 15, 15, 15)
        theme_layout.setSpacing(10)
        current_theme = QLabel(
            "Dark Mode (Recommended)" if self.theme_mode == ThemeMode.DARK else "Light Mode"
        )
        current_theme.setStyleSheet("color: #aaa; font-size: 11px;")
        theme_layout.addWidget(current_theme)
        btn_toggle_theme = QPushButton("🔄 Toggle Theme")
        btn_toggle_theme.setStyleSheet(btn_change.styleSheet())
        btn_toggle_theme.clicked.connect(lambda: [
            self._toggle_theme(),
            current_theme.setText(
                "Dark Mode (Recommended)" if self.theme_mode == ThemeMode.DARK else "Light Mode"
            )
        ])
        theme_layout.addWidget(btn_toggle_theme)
        layout.addWidget(theme_group)

        # Accent color customization
        accent_group = QGroupBox("🎨 Kolor akcentu")
        accent_group.setStyleSheet(wallpaper_group.styleSheet())
        accent_layout = QVBoxLayout(accent_group)
        accent_layout.setContentsMargins(15, 15, 15, 15)
        accent_layout.setSpacing(8)
        accent_info = QLabel("Zmienia kolor przycisków Start, tytułów okien i zaznaczeń.")
        accent_info.setStyleSheet("color: #aaa; font-size: 11px;")
        accent_layout.addWidget(accent_info)
        presets = [
            ("Niebieski", "#3b82f6"),
            ("Zielony", "#22c55e"),
            ("Pomarańczowy", "#f59e0b"),
            ("Czerwony", "#ef4444"),
            ("Szary", "#64748b"),
            ("Fioletowy", "#8b5cf6"),
        ]
        preset_row = QHBoxLayout()
        for name, color in presets:
            b = QPushButton(name)
            b.setStyleSheet(
                f"QPushButton {{ background: {color}; color: white; border: none; "
                f"border-radius: 4px; padding: 8px; font-weight: bold; }}"
            )
            b.clicked.connect(lambda checked=False, c=color: self._set_accent_color(c))
            preset_row.addWidget(b)
        accent_layout.addLayout(preset_row)
        layout.addWidget(accent_group)

        layout.addStretch()
        self.create_window("Display Settings", settings_widget)

    def _set_accent_color(self, color: str):
        """Zapisz i od razu zastosuj kolor akcentu (taskbar, start, ramki)."""
        self.accent_color = color
        try:
            settings_file = self.parent_os.ROOT_DIR / "system" / "desktop_settings.json"
            data = {}
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["accent_color"] = color
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Accent save error: {e}")
        # Natychmiastowe odświeżenie
        self.apply_theme(self.theme_mode)
        self._apply_theme()
        # Start button + taskbar od razu
        if hasattr(self, "taskbar"):
            self.taskbar.apply_theme(self.theme_mode, accent=color)
        QMessageBox.information(self, "Akcent", f"Kolor akcentu: {color}")

    def _show_system_info(self):
        try:
            import platform
            info = f"""
╔═══════════════════════════════════════╗
║   OSmars PC System Information v5.0   ║
╚═══════════════════════════════════════╝
🖥️  System Information
OS: OSmars PC Enhanced Edition
Platform: {platform.system()} {platform.release()}
Machine: {platform.machine()}
Processor: {platform.processor() or 'Unknown'}
🐍 Python Environment
Version: {platform.python_version()}
Implementation: {platform.python_implementation()}
Executable: {sys.executable}
📦 GUI Framework
PySide6: {'✓ Available' if self.parent_os.qt_available else '✗ Not Available'}
WebEngine: {'✓ Available' if self.parent_os.qt_webengine_available else '✗ Not Available'}
📁 File System
Root Directory: {self.parent_os.ROOT_DIR}
Current Directory: {self.parent_os.current_dir}
Available Space: {self._get_available_space()}
🪟 Desktop Environment
Active Windows: {len(self.windows)}
Desktop Icons: {len(self.desktop_icons)}
Theme Mode: {self.theme_mode.value.capitalize()}
Wallpaper: {'Custom' if self.wallpaper_path else 'Default Gradient'}
⏰ System Time
Current Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Uptime: {self._get_uptime()}
"""
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("System Information")
            msg_box.setText(info)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2d2d30;
                    color: white;
                }
                QLabel {
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 11px;
                    white-space: pre;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #3b82f6, stop:1 #2563eb);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 80px;
                }
            """)
            msg_box.exec()
        except Exception as e:
            logger.error(f"System info error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Could not display system information:\n{str(e)}")

    def _get_available_space(self) -> str:
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.parent_os.ROOT_DIR)
            return f"{self._format_size(free)} free of {self._format_size(total)}"
        except Exception:
            return "Unknown"

    def _open_installer(self):
        """Open graphical OSmars disk installer (Live → Disk)."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("💾 Install OSmars to Disk")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #3b82f6;")
        layout.addWidget(title)

        warning = QLabel(
            "⚠️  OSTRZEŻENIE\n\n"
            "To narzędzie instaluje OSmars na wybranym dysku/partycji.\n"
            "WSZYSTKIE DANE NA WYBRANYM DYSKU ZOSTANĄ USUNIĘTE.\n\n"
            "Używaj tylko na maszynie wirtualnej albo na wolnej partycji,\n"
            "dopóki system nie będzie w 100% stabilny.\n\n"
            "Tryb Live (ten, w którym jesteś teraz) NIE nadpisuje dysku\n"
            "dopóki nie potwierdzisz instalacji poniżej."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background: #3d1f1f; color: #ffb4b4; border: 1px solid #e81123; "
            "border-radius: 8px; padding: 14px; font-size: 12px;"
        )
        layout.addWidget(warning)

        layout.addWidget(QLabel("Dostępne dyski:"))
        self._installer_disk_list = QListWidget()
        self._installer_disk_list.setMinimumHeight(140)
        self._installer_disk_list.setStyleSheet(
            "QListWidget { background: #1e1e1e; color: white; border: 1px solid #555; "
            "border-radius: 6px; padding: 6px; } "
            "QListWidget::item:selected { background: #3b82f6; }"
        )
        layout.addWidget(self._installer_disk_list)

        btn_refresh = QPushButton("🔄 Odśwież listę dysków")
        btn_refresh.clicked.connect(self._installer_refresh_disks)
        layout.addWidget(btn_refresh)

        self._installer_log = QPlainTextEdit()
        self._installer_log.setReadOnly(True)
        self._installer_log.setMaximumHeight(120)
        self._installer_log.setPlaceholderText("Log instalacji pojawi się tutaj...")
        self._installer_log.setStyleSheet(
            "background: #1e1e1e; color: #d4d4d4; border: 1px solid #444; "
            "border-radius: 6px; font-family: Consolas, monospace; font-size: 11px;"
        )
        layout.addWidget(self._installer_log)

        btn_row = QHBoxLayout()
        btn_install = QPushButton("⚠  Zainstaluj OSmars na wybranym dysku")
        btn_install.setStyleSheet(
            "QPushButton { background: #e81123; color: white; border: none; "
            "border-radius: 6px; padding: 12px 18px; font-weight: bold; font-size: 13px; } "
            "QPushButton:hover { background: #f13a49; }"
        )
        btn_install.clicked.connect(self._installer_run)
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(lambda: widget.window().close() if widget.window() else None)
        btn_row.addWidget(btn_install)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        layout.addStretch()

        self._installer_refresh_disks()
        self.create_window("OSmars Installer", widget)

    def _installer_get_live_devices(self):
        """Try to detect the Live USB device(s) to exclude from install targets."""
        live = set()
        try:
            # Find device backing / (or /run/live, /lib/live)
            for mount in ("/", "/run/live", "/lib/live", "/cdrom"):
                result = subprocess.run(
                    ["findmnt", "-n", "-o", "SOURCE", mount],
                    capture_output=True, text=True, timeout=5
                )
                src = (result.stdout or "").strip()
                if src.startswith("/dev/"):
                    # strip partition number → whole disk
                    name = src.replace("/dev/", "").rstrip("0123456789")
                    if name.endswith("p") and name[:-1][-1:].isdigit():
                        name = name[:-1]  # nvme0n1p1 → nvme0n1
                    live.add(name)
        except Exception:
            pass
        return live

    def _installer_is_uefi(self) -> bool:
        return Path("/sys/firmware/efi").exists()

    def _installer_refresh_disks(self):
        """List disks via lsblk; mark / exclude Live USB."""
        if not hasattr(self, '_installer_disk_list'):
            return
        self._installer_disk_list.clear()
        live_devs = self._installer_get_live_devices()
        try:
            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,SIZE,MODEL,TYPE"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    name = line.split()[0]
                    if name in live_devs:
                        self._installer_disk_list.addItem(f"{line}  [LIVE – nie wybieraj]")
                    else:
                        self._installer_disk_list.addItem(line)
            else:
                self._installer_disk_list.addItem("(brak dysków / lsblk niedostępne)")
        except FileNotFoundError:
            self._installer_disk_list.addItem("(lsblk nie znaleziony – Windows / brak Linux tools)")
            self._installer_disk_list.addItem("Na Live Linuxie pojawią się prawdziwe dyski.")
        except Exception as e:
            self._installer_disk_list.addItem(f"(błąd: {e})")

    def _installer_run(self):
        """Confirm and run installation steps with strong warnings."""
        item = self._installer_disk_list.currentItem() if hasattr(self, '_installer_disk_list') else None
        if not item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz dysk z listy.")
            return

        disk_line = item.text()
        if disk_line.startswith("("):
            QMessageBox.warning(self, "Brak dysku", "To nie jest prawidłowy dysk.")
            return

        disk_name = disk_line.split()[0]
        device = f"/dev/{disk_name}"

        # Triple confirmation
        reply1 = QMessageBox.warning(
            self, "POTWIERDZENIE 1/3",
            f"Wybrany dysk: {device}\n\n"
            f"{disk_line}\n\n"
            "Wszystkie dane na tym dysku zostaną USUNIĘTE.\n"
            "Kontynuować?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply1 != QMessageBox.Yes:
            return

        reply2 = QMessageBox.critical(
            self, "POTWIERDZENIE 2/3",
            f"OSTATNIA SZANSA\n\n"
            f"Formatowanie {device} (ext4) + instalacja OSmars + GRUB.\n"
            "Naprawdę chcesz to zrobić?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply2 != QMessageBox.Yes:
            return

        typed, ok = QInputDialog.getText(
            self, "POTWIERDZENIE 3/3",
            f"Wpisz dokładnie nazwę urządzenia, żeby potwierdzić:\n\n{device}"
        )
        if not ok or typed.strip() != device:
            QMessageBox.information(self, "Anulowano", "Instalacja anulowana (niepasująca nazwa).")
            return

        if "[LIVE" in disk_line:
            QMessageBox.critical(self, "Live USB", "Nie instaluj na nośniku Live!")
            return

        self._installer_log.appendPlainText(f"=== Instalacja na {device} ===")
        uefi = self._installer_is_uefi()
        self._installer_log.appendPlainText(f"Tryb firmware: {'UEFI' if uefi else 'BIOS/Legacy'}")

        def run_cmd(desc, cmd, check=True):
            self._installer_log.appendPlainText(f"\n→ {desc}")
            self._installer_log.appendPlainText(f"  $ {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.stdout:
                    self._installer_log.appendPlainText(result.stdout[-800:])
                if check and result.returncode != 0:
                    self._installer_log.appendPlainText(f"BŁĄD (kod {result.returncode}):")
                    if result.stderr:
                        self._installer_log.appendPlainText(result.stderr[-800:])
                    QMessageBox.critical(self, "Błąd instalacji", f"Krok nie powiódł się:\n{desc}")
                    return False
                self._installer_log.appendPlainText("  OK")
                return True
            except FileNotFoundError:
                self._installer_log.appendPlainText("  BŁĄD: brak komendy (potrzebny Linux Live + sudo)")
                QMessageBox.critical(self, "Brak narzędzi", "Potrzebujesz Linux Live z mkfs, rsync, grub, sudo.")
                return False
            except Exception as e:
                self._installer_log.appendPlainText(f"  BŁĄD: {e}")
                QMessageBox.critical(self, "Błąd", str(e))
                return False

        target = "/mnt/osmars-install"
        if not run_cmd(f"Formatowanie {device} (ext4)", ["sudo", "mkfs.ext4", "-F", device]):
            return
        if not run_cmd("Tworzenie punktu montowania", ["sudo", "mkdir", "-p", target]):
            return
        if not run_cmd(f"Montowanie {device}", ["sudo", "mount", device, target]):
            return

        # Struktura katalogów
        for d in ("boot", "boot/grub", "boot/efi", "osmars", "bin", "ver"):
            run_cmd(f"mkdir {d}", ["sudo", "mkdir", "-p", f"{target}/{d}"], check=False)

        # Kopiuj OSmars userland
        if not run_cmd(
            "Kopiowanie OSmars (userland)",
            ["sudo", "rsync", "-aAXv",
             str(self.parent_os.ROOT_DIR) + "/",
             f"{target}/osmars/"]
        ):
            return

        # Kernel + initramfs z Live
        self._installer_log.appendPlainText("\n→ Szukanie kernela i initramfs na Live...")
        kernel_candidates = list(Path("/boot").glob("vmlinuz*")) if Path("/boot").exists() else []
        initrd_candidates = []
        if Path("/boot").exists():
            initrd_candidates = list(Path("/boot").glob("initrd*")) + list(Path("/boot").glob("initramfs*"))

        if kernel_candidates:
            ksrc = str(sorted(kernel_candidates)[-1])
            run_cmd("Kopiowanie kernela", ["sudo", "cp", "-a", ksrc, f"{target}/boot/vmlinuz"])
        else:
            self._installer_log.appendPlainText("  ⚠ Brak /boot/vmlinuz* – skopiuj kernel ręcznie później")

        if initrd_candidates:
            isrc = str(sorted(initrd_candidates)[-1])
            run_cmd("Kopiowanie initramfs", ["sudo", "cp", "-a", isrc, f"{target}/boot/initrd.img"])
        else:
            self._installer_log.appendPlainText("  ⚠ Brak initramfs – skopiuj ręcznie później")

        # Python runtime (best-effort z Live)
        for py_path in ("/usr/bin/python3", "/usr/bin/python"):
            if Path(py_path).exists():
                run_cmd("Kopiowanie python3", ["sudo", "cp", "-a", py_path, f"{target}/bin/python3"], check=False)
                break

        # GRUB
        if uefi:
            run_cmd("Montowanie EFIVARFS (jeśli trzeba)", ["sudo", "mount", "-t", "efivarfs", "efivarfs", "/sys/firmware/efi/efivars"], check=False)
            run_cmd(
                "Instalacja GRUB (UEFI)",
                ["sudo", "grub-install", "--target=x86_64-efi",
                 f"--efi-directory={target}/boot/efi",
                 "--bootloader-id=OSmars",
                 f"--boot-directory={target}/boot",
                 device],
                check=False
            )
        else:
            run_cmd(
                "Instalacja GRUB (BIOS)",
                ["sudo", "grub-install", "--target=i386-pc",
                 f"--boot-directory={target}/boot", device]
            )

        # Prosty grub.cfg
        grub_cfg = f"""set timeout=5
set default=0
menuentry "OSmars" {{
    linux /boot/vmlinuz root={device} rw quiet
    initrd /boot/initrd.img
}}
"""
        self._installer_log.appendPlainText("\n→ Zapis grub.cfg")
        try:
            tmp = Path("/tmp/osmars_grub.cfg")
            tmp.write_text(grub_cfg, encoding="utf-8")
            subprocess.run(["sudo", "cp", str(tmp), f"{target}/boot/grub/grub.cfg"], check=False)
            self._installer_log.appendPlainText("  OK")
        except Exception as e:
            self._installer_log.appendPlainText(f"  BŁĄD grub.cfg: {e}")

        run_cmd("Odmontowywanie", ["sudo", "umount", target], check=False)

        self._installer_log.appendPlainText("\n=== INSTALACJA ZAKOŃCZONA ===")
        self._installer_log.appendPlainText("Kernel + initramfs skopiowane (jeśli były na Live).")
        self._installer_log.appendPlainText("Python skopiowany best-effort. Pełny runtime możesz dociągnąć później.")
        QMessageBox.information(
            self, "Sukces",
            f"OSmars zainstalowany na {device} ({'UEFI' if uefi else 'BIOS'}).\n\n"
            "Zrestartuj i wybierz dysk w firmware.\n"
            "Jeśli kernel nie był na Live – dołóż go ręcznie do /boot."
        )

    def _restart_system(self):
        reply = QMessageBox.question(
            self, "Restart System",
            "Are you sure you want to restart the desktop environment?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._save_settings()
            QCoreApplication.exit(1000)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Shutdown OSmars",
            "Are you sure you want to shut down OSmars PC?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._save_settings()
            event.accept()
            self.parent_os._gui_running = False
            logger.info("OSmars Desktop shutdown completed")
        else:
            event.ignore()


def launch_gui_system(parent_os):
    """Launch PySide6 desktop. Only one desktop instance at a time."""
    try:
        if not parent_os.qt_available:
            logger.error("PySide6 not installed. Desktop environment cannot start.")
            print("PySide6 not installed. Install with: pip install pyside6")
            return
        from PySide6 import QtWidgets, QtCore, QtGui

        # Guard: tylko gdy GUI NAPRAWDĘ działa (app + flaga), nie blokuj pierwszego startu
        if getattr(parent_os, "_gui_running", False) and QtWidgets.QApplication.instance() is not None:
            # Sprawdź czy jest już widoczne okno pulpitu
            for w in QtWidgets.QApplication.topLevelWidgets():
                if w.isVisible() and w.__class__.__name__ == "DesktopWindow":
                    logger.warning("GUI already running – ignore second launch")
                    return

        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication(sys.argv)
        app.setStyle("Fusion")

        parent_os._gui_running = True
        while True:
            desktop = DesktopWindow(parent_os)
            desktop.show()
            desktop.raise_()
            desktop.activateWindow()
            exit_code = app.exec()
            # 1000 = restart desktop (from menu), anything else = quit to Recovery
            if exit_code != 1000:
                break
            logger.info("Restarting OSmars Desktop...")
    except Exception as e:
        logger.critical(f"Fatal GUI error: {str(e)}", exc_info=True)
        print(f"Fatal error in GUI system: {str(e)}")
        print("Please check the log file for details.")
    finally:
        parent_os._gui_running = False


# ===========================================
# MAIN ENTRY POINT
# ===========================================
if __name__ == "__main__":
    print("This module should be imported and called via launch_gui_system()")
    print("Example:")
    print("  from gui_system import launch_gui_system")
    print("  launch_gui_system(os_instance)")
