from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QAction, QToolBar,
                             QLabel, QMessageBox, QDialog, QTextEdit, QFrame,
                             QGridLayout, QSlider, QComboBox, QSplitter, QFileDialog,
                             QDockWidget, QScrollArea, QProgressDialog, QSizePolicy,
                             QCheckBox, QSpinBox, QDoubleSpinBox, QActionGroup)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QObject, QEvent
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
from vtk.util import numpy_support
import sys
import os
import numpy as np
import json  

try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False
    print("WARNING: pydicom not installed. Smart scanning disabled.")

vtk_out = vtk.vtkFileOutputWindow()
vtk_out.SetFileName("vtk_errors.log")
vtk.vtkOutputWindow.SetInstance(vtk_out)

# --- THEME STYLING ---
DARK_STYLE = """
QMainWindow {
    background-color: #121212;
}
QMenuBar {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
QMenuBar::item:selected {
    background-color: #3d3d3d;
}
QMenu {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
QMenu::item:selected {
    background-color: #3d3d3d;
}
QToolBar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #3d3d3d;
    spacing: 5px;
}
QToolBar QToolButton {
    color: #e0e0e0;
    background-color: transparent;
    padding: 5px;
}
QToolBar QToolButton:hover {
    background-color: #3d3d3d;
}
QWidget#CentralArea {
    background-color: #000000;
}
QFrame#DashboardPanel {
    background-color: #1e1e1e;
    border: 1px solid #00bcd4;
    border-radius: 4px;
}
QLabel {
    color: #b0b0b0;
    font-family: Arial;
    font-size: 11px;
}
QLabel#HeaderLabel {
    color: #00bcd4;
    font-weight: bold;
    font-size: 12px;
}
QSlider::groove:horizontal {
    border: 1px solid #3d3d3d;
    height: 6px;
    background: #2a2a2a;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00bcd4;
    width: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QPushButton {
    background-color: #2a2a2a;
    color: white;
    border: 1px solid #3d3d3d;
    padding: 6px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #00bcd4;
    color: black;
    border: 1px solid #00bcd4;
}
QPushButton:pressed {
    background-color: #008ba3;
}
QComboBox {
    background-color: #2a2a2a;
    color: white;
    border: 1px solid #3d3d3d;
    padding: 4px;
}
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    color: white;
    selection-background-color: #00bcd4;
}
QDockWidget {
    color: #e0e0e0;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}
QDockWidget::title {
    background-color: #1e1e1e;
    padding: 8px;
    border-bottom: 1px solid #00bcd4;
}
QScrollArea {
    background-color: #121212;
    border: none;
}
"""

SERIES_CARD_STYLE = """
QFrame#SeriesCard {
    background-color: #1e1e1e;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    padding: 5px;
}
QFrame#SeriesCard:hover {
    border: 2px solid #00bcd4;
    background-color: #252525;
}
QFrame#SeriesCardSelected {
    background-color: #1e3a4a;
    border: 2px solid #00bcd4;
    border-radius: 6px;
    padding: 5px;
}
"""

class CameraSettingsDialog(QDialog):
    """Dialog for detailed camera settings."""
    def __init__(self, parent=None, viewport=None, view_name=""):
        super().__init__(parent)
        self.viewport = viewport
        self.view_name = view_name
        self.setWindowTitle(f"Camera Settings - {view_name}")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QGroupBox {
                color: #00bcd4;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                padding: 4px;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #00bcd4;
                color: black;
            }
        """)
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Projection Type
        proj_group = QFrame()
        proj_group.setStyleSheet("QFrame { border: 1px solid #3d3d3d; border-radius: 4px; padding: 10px; }")
        proj_layout = QVBoxLayout(proj_group)
        
        proj_header = QLabel("Projection Type")
        proj_header.setStyleSheet("color: #00bcd4; font-weight: bold; border: none;")
        proj_layout.addWidget(proj_header)
        
        proj_btn_layout = QHBoxLayout()
        self.perspective_btn = QPushButton("Perspective")
        self.perspective_btn.setCheckable(True)
        self.perspective_btn.clicked.connect(lambda: self._set_projection(False))
        proj_btn_layout.addWidget(self.perspective_btn)
        
        self.parallel_btn = QPushButton("Parallel (Ortho)")
        self.parallel_btn.setCheckable(True)
        self.parallel_btn.clicked.connect(lambda: self._set_projection(True))
        proj_btn_layout.addWidget(self.parallel_btn)
        
        proj_layout.addLayout(proj_btn_layout)
        layout.addWidget(proj_group)
        
        # Field of View / Parallel Scale
        fov_group = QFrame()
        fov_group.setStyleSheet("QFrame { border: 1px solid #3d3d3d; border-radius: 4px; padding: 10px; }")
        fov_layout = QVBoxLayout(fov_group)
        
        fov_header = QLabel("View Parameters")
        fov_header.setStyleSheet("color: #00bcd4; font-weight: bold; border: none;")
        fov_layout.addWidget(fov_header)
        
        # FOV slider
        fov_row = QHBoxLayout()
        fov_row.addWidget(QLabel("Field of View:"))
        self.fov_slider = QSlider(Qt.Horizontal)
        self.fov_slider.setRange(5, 120)
        self.fov_slider.setValue(30)
        self.fov_slider.valueChanged.connect(self._on_fov_changed)
        fov_row.addWidget(self.fov_slider)
        self.fov_label = QLabel("30°")
        self.fov_label.setFixedWidth(40)
        self.fov_label.setStyleSheet("color: #00bcd4;")
        fov_row.addWidget(self.fov_label)
        fov_layout.addLayout(fov_row)
        
        # Parallel Scale slider
        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Parallel Scale:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(10, 1000)
        self.scale_slider.setValue(200)
        self.scale_slider.valueChanged.connect(self._on_scale_changed)
        scale_row.addWidget(self.scale_slider)
        self.scale_label = QLabel("200")
        self.scale_label.setFixedWidth(40)
        self.scale_label.setStyleSheet("color: #00bcd4;")
        scale_row.addWidget(self.scale_label)
        fov_layout.addLayout(scale_row)
        
        layout.addWidget(fov_group)
        
        # Clipping Planes
        clip_group = QFrame()
        clip_group.setStyleSheet("QFrame { border: 1px solid #3d3d3d; border-radius: 4px; padding: 10px; }")
        clip_layout = QVBoxLayout(clip_group)
        
        clip_header = QLabel("Clipping Planes")
        clip_header.setStyleSheet("color: #00bcd4; font-weight: bold; border: none;")
        clip_layout.addWidget(clip_header)
        
        near_row = QHBoxLayout()
        near_row.addWidget(QLabel("Near:"))
        self.near_spin = QDoubleSpinBox()
        self.near_spin.setRange(0.01, 10000)
        self.near_spin.setDecimals(2)
        self.near_spin.valueChanged.connect(self._on_clipping_changed)
        near_row.addWidget(self.near_spin)
        clip_layout.addLayout(near_row)
        
        far_row = QHBoxLayout()
        far_row.addWidget(QLabel("Far:"))
        self.far_spin = QDoubleSpinBox()
        self.far_spin.setRange(1, 100000)
        self.far_spin.setDecimals(2)
        self.far_spin.valueChanged.connect(self._on_clipping_changed)
        far_row.addWidget(self.far_spin)
        clip_layout.addLayout(far_row)
        
        layout.addWidget(clip_group)
        
        # Camera Position Info (read-only)
        info_group = QFrame()
        info_group.setStyleSheet("QFrame { border: 1px solid #3d3d3d; border-radius: 4px; padding: 10px; }")
        info_layout = QVBoxLayout(info_group)
        
        info_header = QLabel("Camera Position (Read-Only)")
        info_header.setStyleSheet("color: #00bcd4; font-weight: bold; border: none;")
        info_layout.addWidget(info_header)
        
        self.position_label = QLabel("Position: (0, 0, 0)")
        self.position_label.setStyleSheet("color: #808080; font-size: 10px; border: none;")
        info_layout.addWidget(self.position_label)
        
        self.focal_label = QLabel("Focal Point: (0, 0, 0)")
        self.focal_label.setStyleSheet("color: #808080; font-size: 10px; border: none;")
        info_layout.addWidget(self.focal_label)
        
        self.up_label = QLabel("View Up: (0, 1, 0)")
        self.up_label.setStyleSheet("color: #808080; font-size: 10px; border: none;")
        info_layout.addWidget(self.up_label)
        
        layout.addWidget(info_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self._reset_camera)
        btn_layout.addWidget(reset_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_current_settings(self):
        """Load current camera settings into the dialog."""
        if self.viewport is None:
            return
        
        cam = self.viewport.renderer.GetActiveCamera()
        
        # Projection type
        is_parallel = cam.GetParallelProjection()
        self.parallel_btn.setChecked(is_parallel)
        self.perspective_btn.setChecked(not is_parallel)
        
        # Update button styles
        self._update_projection_buttons(is_parallel)
        
        # FOV and Scale
        self.fov_slider.setValue(int(cam.GetViewAngle()))
        self.fov_label.setText(f"{int(cam.GetViewAngle())}°")
        
        self.scale_slider.setValue(int(cam.GetParallelScale()))
        self.scale_label.setText(f"{int(cam.GetParallelScale())}")
        
        # Clipping planes
        clip_range = cam.GetClippingRange()
        self.near_spin.setValue(clip_range[0])
        self.far_spin.setValue(clip_range[1])
        
        # Position info
        pos = cam.GetPosition()
        focal = cam.GetFocalPoint()
        up = cam.GetViewUp()
        
        self.position_label.setText(f"Position: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")
        self.focal_label.setText(f"Focal Point: ({focal[0]:.1f}, {focal[1]:.1f}, {focal[2]:.1f})")
        self.up_label.setText(f"View Up: ({up[0]:.2f}, {up[1]:.2f}, {up[2]:.2f})")
    
    def _update_projection_buttons(self, is_parallel):
        """Update button styles based on projection type."""
        selected_style = """
            QPushButton {
                background-color: #00bcd4;
                color: black;
                border: 1px solid #00bcd4;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
        """
        default_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #00bcd4;
                color: black;
            }
        """
        
        if is_parallel:
            self.parallel_btn.setStyleSheet(selected_style)
            self.perspective_btn.setStyleSheet(default_style)
            self.scale_slider.setEnabled(True)
            self.fov_slider.setEnabled(False)
        else:
            self.perspective_btn.setStyleSheet(selected_style)
            self.parallel_btn.setStyleSheet(default_style)
            self.scale_slider.setEnabled(False)
            self.fov_slider.setEnabled(True)
    
    def _set_projection(self, parallel):
        """Set the projection type."""
        if self.viewport is None:
            return
        
        cam = self.viewport.renderer.GetActiveCamera()
        cam.SetParallelProjection(parallel)
        self._update_projection_buttons(parallel)
        self.viewport.renderer.ResetCameraClippingRange()
        self.viewport.render()
    
    def _on_fov_changed(self, value):
        """Handle FOV slider change."""
        if self.viewport is None:
            return
        
        self.fov_label.setText(f"{value}°")
        cam = self.viewport.renderer.GetActiveCamera()
        cam.SetViewAngle(value)
        self.viewport.render()
    
    def _on_scale_changed(self, value):
        """Handle parallel scale slider change."""
        if self.viewport is None:
            return
        
        self.scale_label.setText(str(value))
        cam = self.viewport.renderer.GetActiveCamera()
        cam.SetParallelScale(value)
        self.viewport.render()
    
    def _on_clipping_changed(self):
        """Handle clipping plane changes."""
        if self.viewport is None:
            return
        
        near = self.near_spin.value()
        far = self.far_spin.value()
        
        if near < far:
            cam = self.viewport.renderer.GetActiveCamera()
            cam.SetClippingRange(near, far)
            self.viewport.render()
    
    def _reset_camera(self):
        """Reset camera to default."""
        if self.viewport is None:
            return
        
        self.viewport.reset_camera()
        self._load_current_settings()

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Medical DICOM Viewer - Help")
        self.setGeometry(100, 100, 500, 400)
        layout = QVBoxLayout()
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
            <h2>Medical DICOM Viewer - Help</h2>
            <h3>Viewport Layout</h3>
            <ul>
                <li><b>Top-Left:</b> Axial View (Top-down)</li>
                <li><b>Top-Right:</b> Sagittal View (Side)</li>
                <li><b>Bottom-Left:</b> Coronal View (Front)</li>
                <li><b>Bottom-Right:</b> 3D Volume View (Free rotation)</li>
            </ul>
            <h3>Smart Scan</h3>
            <ul>
                <li><b>Smart Scan:</b> Recursively scans folders for DICOM series</li>
                <li><b>Series Cards:</b> Click to load a specific series</li>
                <li><b>Thumbnails:</b> Preview of middle slice</li>
            </ul>
            <h3>Controls</h3>
            <ul>
                <li><b>Left Mouse:</b> Rotate (3D) / Pan (2D)</li>
                <li><b>Right Mouse:</b> Zoom</li>
                <li><b>Middle Mouse:</b> Pan</li>
                <li><b>Scroll:</b> Slice through (2D views)</li>
            </ul>
        """)
        layout.addWidget(help_text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        self.setLayout(layout)


# ============================================================================
# DICOM SCANNER - Recursive Smart Scan with Series Grouping
# ============================================================================

class DicomScannerThread(QThread):
    """Background thread for scanning DICOM directories."""
    progress = pyqtSignal(int, str)  # progress percentage, status message
    finished_scanning = pyqtSignal(dict)  # series_dict
    error = pyqtSignal(str)
    
    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        """Recursively scan for DICOM files and group by SeriesInstanceUID."""
        if not HAS_PYDICOM:
            self.error.emit("pydicom is not installed. Please install it with: pip install pydicom")
            return
        
        series_dict = {}  # Key: SeriesInstanceUID, Value: SeriesInfo dict
        all_files = []
        
        # First pass: collect all potential files
        self.progress.emit(0, "Scanning directories...")
        try:
            for root, dirs, files in os.walk(self.root_path):
                if self._is_cancelled:
                    return
                for filename in files:
                    filepath = os.path.join(root, filename)
                    all_files.append(filepath)
        except Exception as e:
            self.error.emit(f"Error scanning directories: {e}")
            return
        
        total_files = len(all_files)
        if total_files == 0:
            self.error.emit("No files found in the selected directory.")
            return
        
        # Second pass: read DICOM headers and group by series
        self.progress.emit(5, f"Analyzing {total_files} files...")
        
        for idx, filepath in enumerate(all_files):
            if self._is_cancelled:
                return
            
            # Update progress every 10 files
            if idx % 10 == 0:
                progress_pct = 5 + int((idx / total_files) * 90)
                self.progress.emit(progress_pct, f"Processing file {idx+1}/{total_files}")
            
            try:
                # Read only header (stop_before_pixels for speed)
                dcm = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
                
                # Skip non-image DICOM files
                if not hasattr(dcm, 'PixelData') and not hasattr(dcm, 'Rows'):
                    # Check if it's likely an image by checking for required attributes
                    if not hasattr(dcm, 'SeriesInstanceUID'):
                        continue
                
                series_uid = str(getattr(dcm, 'SeriesInstanceUID', 'Unknown'))
                
                if series_uid not in series_dict:
                    # Extract metadata for this series
                    series_dict[series_uid] = {
                        'series_uid': series_uid,
                        'series_description': str(getattr(dcm, 'SeriesDescription', 'No Description')),
                        'series_number': str(getattr(dcm, 'SeriesNumber', '')),
                        'modality': str(getattr(dcm, 'Modality', 'Unknown')),
                        'patient_name': str(getattr(dcm, 'PatientName', 'Anonymous')),
                        'study_date': str(getattr(dcm, 'StudyDate', '')),
                        'study_description': str(getattr(dcm, 'StudyDescription', '')),
                        'rows': int(getattr(dcm, 'Rows', 0)),
                        'columns': int(getattr(dcm, 'Columns', 0)),
                        'file_paths': [],
                        'instance_numbers': []
                    }
                
                # Add file path
                series_dict[series_uid]['file_paths'].append(filepath)
                
                # Store instance number for sorting
                instance_num = int(getattr(dcm, 'InstanceNumber', 0))
                series_dict[series_uid]['instance_numbers'].append((instance_num, filepath))
                
            except InvalidDicomError:
                continue  # Not a DICOM file
            except Exception as e:
                continue  # Skip problematic files
        
        # Sort files within each series by instance number
        self.progress.emit(95, "Sorting series...")
        for series_uid, series_info in series_dict.items():
            if series_info['instance_numbers']:
                sorted_files = sorted(series_info['instance_numbers'], key=lambda x: x[0])
                series_info['file_paths'] = [f[1] for f in sorted_files]
            series_info['num_images'] = len(series_info['file_paths'])
        
        self.progress.emit(100, f"Found {len(series_dict)} series")
        self.finished_scanning.emit(series_dict)


class SeriesCard(QFrame):
    """A clickable card widget representing a DICOM series."""
    clicked = pyqtSignal(str)  # Emits series_uid when clicked
    
    def __init__(self, series_info, parent=None):
        super().__init__(parent)
        self.series_uid = series_info['series_uid']
        self.series_info = series_info
        self.is_selected = False
        self.thumbnail_pixmap = None
        
        self.setObjectName("SeriesCard")
        self.setStyleSheet(SERIES_CARD_STYLE)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(100)
        self.setMinimumWidth(200)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Thumbnail placeholder
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(80, 80)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setText("...")
        layout.addWidget(self.thumbnail_label)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Series description
        desc = self.series_info.get('series_description', 'No Description')
        if len(desc) > 25:
            desc = desc[:22] + "..."
        self.desc_label = QLabel(desc)
        self.desc_label.setStyleSheet("color: #00bcd4; font-weight: bold; font-size: 12px;")
        info_layout.addWidget(self.desc_label)
        
        # Modality and series number
        modality = self.series_info.get('modality', 'Unknown')
        series_num = self.series_info.get('series_number', '')
        mod_text = f"{modality}" + (f" - Series {series_num}" if series_num else "")
        self.modality_label = QLabel(mod_text)
        self.modality_label.setStyleSheet("color: #e0e0e0; font-size: 10px;")
        info_layout.addWidget(self.modality_label)
        
        # Number of images
        num_images = self.series_info.get('num_images', 0)
        self.count_label = QLabel(f"{num_images} images")
        self.count_label.setStyleSheet("color: #808080; font-size: 10px;")
        info_layout.addWidget(self.count_label)
        
        # Dimensions
        rows = self.series_info.get('rows', 0)
        cols = self.series_info.get('columns', 0)
        if rows and cols:
            self.dims_label = QLabel(f"{cols} x {rows}")
            self.dims_label.setStyleSheet("color: #606060; font-size: 9px;")
            info_layout.addWidget(self.dims_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, stretch=1)
    
    def set_thumbnail(self, pixmap):
        """Set the thumbnail image."""
        if pixmap:
            self.thumbnail_pixmap = pixmap
            scaled = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled)
    
    def set_selected(self, selected):
        """Update selection state."""
        self.is_selected = selected
        if selected:
            self.setObjectName("SeriesCardSelected")
        else:
            self.setObjectName("SeriesCard")
        self.setStyleSheet(SERIES_CARD_STYLE)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.series_uid)
        super().mousePressEvent(event)

class StudyBrowser(QWidget):
    """Sidebar widget for browsing DICOM studies and series."""
    series_selected = pyqtSignal(dict)  # Emits series_info when selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.series_dict = {}
        self.series_cards = {}
        self.selected_series_uid = None
        self.scanner_thread = None
        
        # Set background for the entire widget
        self.setStyleSheet("background-color: #121212;")
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Header
        header = QLabel("SMART SCAN")
        header.setStyleSheet("""
            color: #00bcd4;
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #1e1e1e;
            border-radius: 4px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Scan button
        self.scan_btn = QPushButton("📁 Import Root Folder")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #00bcd4;
                color: black;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #00acc1;
            }
        """)
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self.scan_btn)
        
        # Status label
        self.status_label = QLabel("No study loaded")
        self.status_label.setStyleSheet("color: #808080; font-size: 10px; background-color: transparent;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Scroll area for series cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #121212;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #121212;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00bcd4;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #1e1e1e;
            }
        """)
        
        # Container for cards - THIS IS THE KEY FIX
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: #121212;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(5, 5, 5, 5)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area, stretch=1)

    def _on_scan_clicked(self):
        """Open directory dialog and start scanning."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select DICOM Root Directory",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if directory:
            self.start_scan(directory)
    
    def start_scan(self, root_path):
        """Start the background scanning thread."""
        if self.scanner_thread and self.scanner_thread.isRunning():
            self.scanner_thread.cancel()
            self.scanner_thread.wait()
        
        # Clear existing cards
        self._clear_cards()
        
        # Create progress dialog
        self.progress_dialog = QProgressDialog("Scanning...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Import Root Folder")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        
        # Start scanner thread
        self.scanner_thread = DicomScannerThread(root_path)
        self.scanner_thread.progress.connect(self._on_scan_progress)
        self.scanner_thread.finished_scanning.connect(self._on_scan_finished)
        self.scanner_thread.error.connect(self._on_scan_error)
        self.progress_dialog.canceled.connect(self.scanner_thread.cancel)
        
        self.scanner_thread.start()
    
    def _on_scan_progress(self, percent, message):
        """Update progress dialog."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(percent)
            self.progress_dialog.setLabelText(message)
    
    def _on_scan_finished(self, series_dict):
        """Handle scan completion."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        self.series_dict = series_dict
        self._populate_cards()
        
        num_series = len(series_dict)
        total_images = sum(s.get('num_images', 0) for s in series_dict.values())
        self.status_label.setText(f"{num_series} series, {total_images} total images")
    
    def _on_scan_error(self, error_msg):
        """Handle scan error."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        
        QMessageBox.warning(self, "Scan Error", error_msg)
        self.status_label.setText("Scan failed")
    
    def _clear_cards(self):
        """Remove all series cards."""
        for card in self.series_cards.values():
            card.deleteLater()
        self.series_cards.clear()
        
        # Clear layout
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _populate_cards(self):
        """Create cards for all series."""
        # Sort series by series number
        sorted_series = sorted(
            self.series_dict.values(),
            key=lambda x: (x.get('series_number', '0').zfill(10), x.get('series_description', ''))
        )
        
        for series_info in sorted_series:
            card = SeriesCard(series_info)
            card.clicked.connect(self._on_card_clicked)
            
            # Insert before the stretch
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self.series_cards[series_info['series_uid']] = card
            
            # Generate thumbnail in background
            self._generate_thumbnail(series_info, card)
    
    def _generate_thumbnail(self, series_info, card):
        """Generate thumbnail from middle slice."""
        if not HAS_PYDICOM:
            return
        
        file_paths = series_info.get('file_paths', [])
        if not file_paths:
            return
        
        # Get middle slice
        middle_idx = len(file_paths) // 2
        try:
            dcm = pydicom.dcmread(file_paths[middle_idx])
            if hasattr(dcm, 'pixel_array'):
                pixel_array = dcm.pixel_array
                
                # Normalize to 8-bit
                if pixel_array.dtype != np.uint8:
                    # Apply window/level for better visualization
                    window_center = getattr(dcm, 'WindowCenter', None)
                    window_width = getattr(dcm, 'WindowWidth', None)
                    
                    if isinstance(window_center, pydicom.multival.MultiValue):
                        window_center = window_center[0]
                    if isinstance(window_width, pydicom.multival.MultiValue):
                        window_width = window_width[0]
                    
                    if window_center is not None and window_width is not None:
                        window_center = float(window_center)
                        window_width = float(window_width)
                        min_val = window_center - window_width / 2
                        max_val = window_center + window_width / 2
                    else:
                        min_val = pixel_array.min()
                        max_val = pixel_array.max()
                    
                    if max_val > min_val:
                        pixel_array = np.clip(pixel_array, min_val, max_val)
                        pixel_array = ((pixel_array - min_val) / (max_val - min_val) * 255).astype(np.uint8)
                    else:
                        pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)
                
                # Handle multi-frame or RGB
                if len(pixel_array.shape) == 3:
                    if pixel_array.shape[2] == 3:  # RGB
                        height, width, _ = pixel_array.shape
                        bytes_per_line = 3 * width
                        qimage = QImage(pixel_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    else:  # Multi-frame, take first
                        pixel_array = pixel_array[0]
                        height, width = pixel_array.shape
                        qimage = QImage(pixel_array.data, width, height, width, QImage.Format_Grayscale8)
                else:
                    height, width = pixel_array.shape
                    qimage = QImage(pixel_array.tobytes(), width, height, width, QImage.Format_Grayscale8)
                
                pixmap = QPixmap.fromImage(qimage)
                card.set_thumbnail(pixmap)
                
        except Exception as e:
            print(f"Thumbnail generation failed for {series_info['series_uid']}: {e}")
    
    def _on_card_clicked(self, series_uid):
        """Handle series card click."""
        # Update selection state
        if self.selected_series_uid and self.selected_series_uid in self.series_cards:
            self.series_cards[self.selected_series_uid].set_selected(False)
        
        self.selected_series_uid = series_uid
        if series_uid in self.series_cards:
            self.series_cards[series_uid].set_selected(True)
        
        # Emit signal with series info
        if series_uid in self.series_dict:
            self.series_selected.emit(self.series_dict[series_uid])

class CrosshairManager(QObject):
    """Manages synchronized crosshair position across all MPR views."""
    position_changed = pyqtSignal(float, float, float)  # x, y, z
    
    def __init__(self):
        super().__init__()
        self._current_center = [0.0, 0.0, 0.0]  # x, y, z in world coordinates
        self._image_bounds = [0, 1, 0, 1, 0, 1]  # xmin, xmax, ymin, ymax, zmin, zmax
        self._enabled = False
    
    @property
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, value):
        self._enabled = value
    
    @property
    def current_center(self):
        return tuple(self._current_center)
    
    def set_image_bounds(self, bounds):
        """Set the bounds of the image volume."""
        self._image_bounds = list(bounds)
        # Initialize center to middle of volume
        self._current_center = [
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0
        ]
    
    def set_position(self, x=None, y=None, z=None, emit=True):
        """Update the crosshair position. Only updates provided coordinates."""
        changed = False
        
        if x is not None:
            x = max(self._image_bounds[0], min(self._image_bounds[1], x))
            if self._current_center[0] != x:
                self._current_center[0] = x
                changed = True
        
        if y is not None:
            y = max(self._image_bounds[2], min(self._image_bounds[3], y))
            if self._current_center[1] != y:
                self._current_center[1] = y
                changed = True
        
        if z is not None:
            z = max(self._image_bounds[4], min(self._image_bounds[5], z))
            if self._current_center[2] != z:
                self._current_center[2] = z
                changed = True
        
        if changed and emit and self._enabled:
            self.position_changed.emit(*self._current_center)
    
    def set_position_xyz(self, x, y, z, emit=True):
        """Set all coordinates at once."""
        self.set_position(x, y, z, emit=emit)
    
    def get_bounds(self):
        """Return current image bounds."""
        return tuple(self._image_bounds)


# ============================================================================
# VTK HANDLER
# ============================================================================

class myVTK:
    """Core VTK Logic for managing volume data."""
    
    def __init__(self):
        self.imageData = None
        self.reader = None
        self.volumeProperty = vtk.vtkVolumeProperty()
        self.gradientOpacity = vtk.vtkPiecewiseFunction()
        self.scalarOpacity = vtk.vtkPiecewiseFunction()
        self.color = vtk.vtkColorTransferFunction()
        self.is_loaded = False
        self.is_2d = False
        
        self._init_volume_property()
    
    def _init_volume_property(self):
        """Initialize volume property with default settings."""
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(0.4)
        self.volumeProperty.SetDiffuse(0.6)
        self.volumeProperty.SetSpecular(0.2)
    
    def load_dicom(self, directory_path):
        """Load DICOM from a directory path using VTK reader."""
        try:
            if os.path.isfile(directory_path):
                directory_path = os.path.dirname(directory_path)
            
            self.reader = vtk.vtkDICOMImageReader()
            self.reader.SetDirectoryName(directory_path)
            self.reader.Update()
            
            output = self.reader.GetOutput()
            if output is None or output.GetNumberOfPoints() == 0:
                print(f"No DICOM data found in: {directory_path}")
                return False
            
            dims = output.GetDimensions()
            print(f"Loaded DICOM from: {directory_path}")
            print(f"Image dimensions: {dims}")
            print(f"Scalar range: {output.GetScalarRange()}")
            
            if dims[0] <= 0 or dims[1] <= 0:
                print("ERROR: Invalid image dimensions")
                return False
            
            self.is_2d = dims[2] <= 1
            
            max_dim = max(dims[0], dims[1], dims[2])
            if max_dim > 2048:
                self.imageData = self._resample_image(output, 2048)
            else:
                self.imageData = vtk.vtkImageData()
                self.imageData.DeepCopy(output)
            
            self.setup_bone_preset()
            self.is_loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading DICOM: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_from_file_list(self, file_paths):
        """Load DICOM from a list of file paths using pydicom + VTK."""
        if not HAS_PYDICOM:
            # Fallback to directory-based loading
            if file_paths:
                return self.load_dicom(os.path.dirname(file_paths[0]))
            return False
        
        try:
            if not file_paths:
                print("No files provided")
                return False
            
            print(f"Loading {len(file_paths)} DICOM files...")
            
            # Read all slices
            slices = []
            for fp in file_paths:
                try:
                    dcm = pydicom.dcmread(fp)
                    if hasattr(dcm, 'pixel_array'):
                        slices.append(dcm)
                except Exception as e:
                    print(f"Skipping file {fp}: {e}")
                    continue
            
            if not slices:
                print("No valid DICOM images found")
                return False
            
            # Store window/level from DICOM metadata
            window_center = getattr(slices[0], 'WindowCenter', None)
            window_width = getattr(slices[0], 'WindowWidth', None)
            
            if isinstance(window_center, pydicom.multival.MultiValue):
                window_center = window_center[0]
            if isinstance(window_width, pydicom.multival.MultiValue):
                window_width = window_width[0]
            
            # Store for later use in viewports
            self.dicom_window = float(window_width) if window_width else None
            self.dicom_level = float(window_center) if window_center else None
            
            print(f"DICOM Window/Level: {self.dicom_window}/{self.dicom_level}")
            
            # Sort by ImagePositionPatient or InstanceNumber
            try:
                slices.sort(key=lambda x: float(x.ImagePositionPatient[2]) if hasattr(x, 'ImagePositionPatient') else float(getattr(x, 'InstanceNumber', 0)))
            except:
                slices.sort(key=lambda x: float(getattr(x, 'InstanceNumber', 0)))
            
            # Get dimensions
            rows = int(slices[0].Rows)
            cols = int(slices[0].Columns)
            num_slices = len(slices)
            
            print(f"Creating volume: {cols} x {rows} x {num_slices}")
            
            # === DEBUG: Print all spacing-related DICOM tags ===
            print("=== DICOM Spacing Debug ===")
            dcm = slices[0]
            print(f"  PixelSpacing: {getattr(dcm, 'PixelSpacing', 'NOT FOUND')}")
            print(f"  ImagerPixelSpacing: {getattr(dcm, 'ImagerPixelSpacing', 'NOT FOUND')}")
            print(f"  SliceThickness: {getattr(dcm, 'SliceThickness', 'NOT FOUND')}")
            print(f"  SpacingBetweenSlices: {getattr(dcm, 'SpacingBetweenSlices', 'NOT FOUND')}")
            print(f"  ImagePositionPatient: {getattr(dcm, 'ImagePositionPatient', 'NOT FOUND')}")
            
            # Check for Enhanced DICOM (multi-frame) spacing in PerFrameFunctionalGroupsSequence
            if hasattr(dcm, 'PerFrameFunctionalGroupsSequence'):
                print("  Enhanced DICOM detected - checking PerFrameFunctionalGroupsSequence...")
                try:
                    frame0 = dcm.PerFrameFunctionalGroupsSequence[0]
                    if hasattr(frame0, 'PixelMeasuresSequence'):
                        pm = frame0.PixelMeasuresSequence[0]
                        print(f"    PixelSpacing (from PerFrame): {getattr(pm, 'PixelSpacing', 'NOT FOUND')}")
                        print(f"    SliceThickness (from PerFrame): {getattr(pm, 'SliceThickness', 'NOT FOUND')}")
                except Exception as e:
                    print(f"    Error reading PerFrame: {e}")
            
            if hasattr(dcm, 'SharedFunctionalGroupsSequence'):
                print("  Checking SharedFunctionalGroupsSequence...")
                try:
                    shared = dcm.SharedFunctionalGroupsSequence[0]
                    if hasattr(shared, 'PixelMeasuresSequence'):
                        pm = shared.PixelMeasuresSequence[0]
                        print(f"    PixelSpacing (from Shared): {getattr(pm, 'PixelSpacing', 'NOT FOUND')}")
                        print(f"    SliceThickness (from Shared): {getattr(pm, 'SliceThickness', 'NOT FOUND')}")
                except Exception as e:
                    print(f"    Error reading Shared: {e}")
            print("=== End Spacing Debug ===")
            
            # === ENHANCED: PROPERLY READ PIXEL SPACING ===
            pixel_spacing = None
            
            # Method 1: Standard PixelSpacing tag
            pixel_spacing_raw = getattr(slices[0], 'PixelSpacing', None)
            if pixel_spacing_raw is not None:
                if isinstance(pixel_spacing_raw, pydicom.multival.MultiValue):
                    pixel_spacing = [float(pixel_spacing_raw[0]), float(pixel_spacing_raw[1])]
                else:
                    pixel_spacing = [float(pixel_spacing_raw), float(pixel_spacing_raw)]
                print(f"PixelSpacing found (standard): {pixel_spacing}")
            
            # Method 2: ImagerPixelSpacing (common in CR/DX)
            if pixel_spacing is None:
                imager_spacing = getattr(slices[0], 'ImagerPixelSpacing', None)
                if imager_spacing is not None:
                    if isinstance(imager_spacing, pydicom.multival.MultiValue):
                        pixel_spacing = [float(imager_spacing[0]), float(imager_spacing[1])]
                    else:
                        pixel_spacing = [float(imager_spacing), float(imager_spacing)]
                    print(f"PixelSpacing found (ImagerPixelSpacing): {pixel_spacing}")
            
            # Method 3: Enhanced DICOM - SharedFunctionalGroupsSequence
            if pixel_spacing is None:
                try:
                    if hasattr(slices[0], 'SharedFunctionalGroupsSequence'):
                        shared = slices[0].SharedFunctionalGroupsSequence[0]
                        if hasattr(shared, 'PixelMeasuresSequence'):
                            pm = shared.PixelMeasuresSequence[0]
                            if hasattr(pm, 'PixelSpacing'):
                                ps = pm.PixelSpacing
                                pixel_spacing = [float(ps[0]), float(ps[1])]
                                print(f"PixelSpacing found (SharedFunctionalGroups): {pixel_spacing}")
                except Exception as e:
                    print(f"Error reading SharedFunctionalGroupsSequence: {e}")
            
            # Method 4: Enhanced DICOM - PerFrameFunctionalGroupsSequence
            if pixel_spacing is None:
                try:
                    if hasattr(slices[0], 'PerFrameFunctionalGroupsSequence'):
                        frame = slices[0].PerFrameFunctionalGroupsSequence[0]
                        if hasattr(frame, 'PixelMeasuresSequence'):
                            pm = frame.PixelMeasuresSequence[0]
                            if hasattr(pm, 'PixelSpacing'):
                                ps = pm.PixelSpacing
                                pixel_spacing = [float(ps[0]), float(ps[1])]
                                print(f"PixelSpacing found (PerFrameFunctionalGroups): {pixel_spacing}")
                except Exception as e:
                    print(f"Error reading PerFrameFunctionalGroupsSequence: {e}")
            
            # Method 5: Default fallback
            if pixel_spacing is None:
                pixel_spacing = [1.0, 1.0]
                print("WARNING: No PixelSpacing found in any location, using default 1.0 mm")
            
            # === ENHANCED: PROPERLY READ SLICE THICKNESS / SPACING ===
            slice_thickness = None
            
            # Method 1: Calculate from ImagePositionPatient (most accurate)
            if num_slices > 1:
                try:
                    pos1 = getattr(slices[0], 'ImagePositionPatient', None)
                    pos2 = getattr(slices[1], 'ImagePositionPatient', None)
                    if pos1 is not None and pos2 is not None:
                        slice_spacing = ((float(pos2[0]) - float(pos1[0]))**2 + 
                                        (float(pos2[1]) - float(pos1[1]))**2 + 
                                        (float(pos2[2]) - float(pos1[2]))**2) ** 0.5
                        if slice_spacing > 0:
                            slice_thickness = slice_spacing
                            print(f"SliceSpacing (from ImagePositionPatient): {slice_thickness:.4f} mm")
                except Exception as e:
                    print(f"Could not calculate slice spacing from position: {e}")
            
            # Method 2: SpacingBetweenSlices
            if slice_thickness is None:
                spacing_between = getattr(slices[0], 'SpacingBetweenSlices', None)
                if spacing_between is not None:
                    slice_thickness = abs(float(spacing_between))
                    print(f"SliceSpacing (from SpacingBetweenSlices): {slice_thickness:.4f} mm")
            
            # Method 3: SliceThickness
            if slice_thickness is None:
                thickness_attr = getattr(slices[0], 'SliceThickness', None)
                if thickness_attr is not None:
                    slice_thickness = float(thickness_attr)
                    print(f"SliceThickness: {slice_thickness:.4f} mm")
            
            # Method 4: Enhanced DICOM sequences
            if slice_thickness is None:
                try:
                    if hasattr(slices[0], 'SharedFunctionalGroupsSequence'):
                        shared = slices[0].SharedFunctionalGroupsSequence[0]
                        if hasattr(shared, 'PixelMeasuresSequence'):
                            pm = shared.PixelMeasuresSequence[0]
                            if hasattr(pm, 'SliceThickness'):
                                slice_thickness = float(pm.SliceThickness)
                                print(f"SliceThickness (from SharedFunctionalGroups): {slice_thickness:.4f} mm")
                except:
                    pass
            
            # Method 5: Default fallback
            if slice_thickness is None or slice_thickness <= 0:
                slice_thickness = 1.0
                print("WARNING: No slice spacing found, using default 1.0 mm")
            
            # Final spacing: VTK uses (x_spacing, y_spacing, z_spacing)
            # PixelSpacing is (row_spacing, col_spacing) = (y, x) in image coordinates
            final_spacing = (float(pixel_spacing[1]), float(pixel_spacing[0]), float(slice_thickness))
            print(f"=== FINAL VTK Spacing (X, Y, Z): {final_spacing[0]:.4f}, {final_spacing[1]:.4f}, {final_spacing[2]:.4f} mm ===")
            
            # Handle different pixel array shapes (RGB, multi-frame, etc.)
            sample_array = slices[0].pixel_array
            
            if len(sample_array.shape) == 3:
                if sample_array.shape[2] in [3, 4]:  # RGB or RGBA
                    # Convert RGB to grayscale for volume rendering
                    print("Converting RGB to grayscale...")
                    sample_array = np.mean(sample_array[:, :, :3], axis=2)
                elif sample_array.shape[0] < sample_array.shape[1] and sample_array.shape[0] < sample_array.shape[2]:
                    # Multi-frame: shape is (frames, rows, cols)
                    print(f"Multi-frame DICOM detected: {sample_array.shape[0]} frames")
                    # Use frames as slices
                    multi_frame = sample_array
                    rows, cols = multi_frame.shape[1], multi_frame.shape[2]
                    num_slices = multi_frame.shape[0]
                    
                    # Determine dtype
                    if multi_frame.dtype == np.uint16:
                        numpy_dtype = np.int16
                        vtk_dtype = vtk.VTK_SHORT
                    elif multi_frame.dtype == np.int16:
                        numpy_dtype = np.int16
                        vtk_dtype = vtk.VTK_SHORT
                    elif multi_frame.dtype == np.uint8:
                        numpy_dtype = np.uint8
                        vtk_dtype = vtk.VTK_UNSIGNED_CHAR
                    else:
                        numpy_dtype = np.int16
                        vtk_dtype = vtk.VTK_SHORT
                    
                    # Create volume from multi-frame
                    volume = np.zeros((cols, rows, num_slices), dtype=numpy_dtype)
                    for i in range(num_slices):
                        frame = multi_frame[i].astype(np.float32)
                        slope = float(getattr(slices[0], 'RescaleSlope', 1) or 1)
                        intercept = float(getattr(slices[0], 'RescaleIntercept', 0) or 0)
                        if slope != 1 or intercept != 0:
                            frame = frame * slope + intercept
                        volume[:, :, i] = frame.T.astype(numpy_dtype)
                    
                    # Create VTK image data
                    self.imageData = vtk.vtkImageData()
                    self.imageData.SetDimensions(cols, rows, num_slices)
                    self.imageData.SetSpacing(final_spacing[0], final_spacing[1], final_spacing[2])
                    self.imageData.SetOrigin(0, 0, 0)
                    
                    vtk_data_array = numpy_support.numpy_to_vtk(
                        volume.ravel(order='F'),
                        deep=True,
                        array_type=vtk_dtype
                    )
                    self.imageData.GetPointData().SetScalars(vtk_data_array)
                    
                    dims = self.imageData.GetDimensions()
                    print(f"VTK volume dimensions: {dims}")
                    print(f"Scalar range: {self.imageData.GetScalarRange()}")
                    
                    self.is_2d = dims[2] <= 1
                    self.setup_mri_preset()
                    self.is_loaded = True
                    return True
            
            # Standard dtype determination
            if sample_array.dtype == np.uint16:
                numpy_dtype = np.int16
                vtk_dtype = vtk.VTK_SHORT
            elif sample_array.dtype == np.int16:
                numpy_dtype = np.int16
                vtk_dtype = vtk.VTK_SHORT
            elif sample_array.dtype == np.uint8:
                numpy_dtype = np.uint8
                vtk_dtype = vtk.VTK_UNSIGNED_CHAR
            else:
                numpy_dtype = np.int16
                vtk_dtype = vtk.VTK_SHORT
            
            # Handle single slice case - create a thin volume
            if num_slices == 1:
                print("Single slice detected - creating 2D view")
                num_slices = 1  # Keep as 1 for 2D display
            
            # Create numpy array with correct VTK ordering (cols, rows, slices) = (x, y, z)
            volume = np.zeros((cols, rows, num_slices), dtype=numpy_dtype)
            
            for i, s in enumerate(slices):
                pixel_array = s.pixel_array.astype(np.float32)
                
                # Handle RGB images
                if len(pixel_array.shape) == 3 and pixel_array.shape[2] in [3, 4]:
                    pixel_array = np.mean(pixel_array[:, :, :3], axis=2)
                
                # Apply rescale if present (for CT Hounsfield units)
                slope = float(getattr(s, 'RescaleSlope', 1) or 1)
                intercept = float(getattr(s, 'RescaleIntercept', 0) or 0)
                if slope != 1 or intercept != 0:
                    pixel_array = pixel_array * slope + intercept
                
                # Transpose from (rows, cols) to (cols, rows) for VTK's x,y ordering
                volume[:, :, i] = pixel_array.T.astype(numpy_dtype)
            
            # Create VTK image data
            self.imageData = vtk.vtkImageData()
            self.imageData.SetDimensions(cols, rows, num_slices)
            
            # === FIX: USE CORRECTLY EXTRACTED SPACING ===
            self.imageData.SetSpacing(final_spacing[0], final_spacing[1], final_spacing[2])
            
            # Set origin from first slice
            if hasattr(slices[0], 'ImagePositionPatient') and slices[0].ImagePositionPatient is not None:
                try:
                    origin = slices[0].ImagePositionPatient
                    self.imageData.SetOrigin(float(origin[0]), float(origin[1]), float(origin[2]))
                except:
                    self.imageData.SetOrigin(0, 0, 0)
            else:
                self.imageData.SetOrigin(0, 0, 0)
            
            # Flatten in Fortran order (column-major) which is what VTK expects
            vtk_data_array = numpy_support.numpy_to_vtk(
                volume.ravel(order='F'),
                deep=True,
                array_type=vtk_dtype
            )
            self.imageData.GetPointData().SetScalars(vtk_data_array)
            
            # Check dimensions and spacing
            dims = self.imageData.GetDimensions()
            spacing = self.imageData.GetSpacing()
            bounds = self.imageData.GetBounds()
            
            print(f"VTK volume dimensions: {dims}")
            print(f"VTK spacing: {spacing}")
            print(f"VTK bounds: X=[{bounds[0]:.1f}, {bounds[1]:.1f}], Y=[{bounds[2]:.1f}, {bounds[3]:.1f}], Z=[{bounds[4]:.1f}, {bounds[5]:.1f}]")
            print(f"Physical size: {bounds[1]-bounds[0]:.1f} x {bounds[3]-bounds[2]:.1f} x {bounds[5]-bounds[4]:.1f} mm")
            print(f"Scalar range: {self.imageData.GetScalarRange()}")
            
            self.is_2d = dims[2] <= 1
            
            # Setup appropriate preset based on modality
            modality = str(getattr(slices[0], 'Modality', 'CT') or 'CT')
            print(f"Detected modality: {modality}")
            
            # Use auto-detection for best results
            self.setup_auto_preset()
            
            self.is_loaded = True
            
            return True
            
        except Exception as e:
            print(f"Error loading from file list: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def setup_mri_preset(self):
        """Setup MRI visualization preset - auto-adjusts to data range."""
        if self.imageData is None:
            return
        
        # Get actual data range
        scalar_range = self.imageData.GetScalarRange()
        min_val, max_val = scalar_range
        data_range = max_val - min_val
        
        print(f"MRI Preset - Data range: {min_val} to {max_val}")
        
        # Calculate percentile-based thresholds
        # For MRI, we want to show soft tissue primarily
        low_thresh = min_val + data_range * 0.05   # 5% - background cutoff
        mid_low = min_val + data_range * 0.15     # 15%
        mid = min_val + data_range * 0.35         # 35%
        mid_high = min_val + data_range * 0.60   # 60%
        high = min_val + data_range * 0.85       # 85%
        
        self.scalarOpacity.RemoveAllPoints()
        self.scalarOpacity.AddPoint(min_val, 0.0)
        self.scalarOpacity.AddPoint(low_thresh, 0.0)      # Background transparent
        self.scalarOpacity.AddPoint(mid_low, 0.05)        # Start showing
        self.scalarOpacity.AddPoint(mid, 0.15)            # Soft tissue
        self.scalarOpacity.AddPoint(mid_high, 0.3)        # Denser tissue
        self.scalarOpacity.AddPoint(high, 0.5)            # Bone/bright areas
        self.scalarOpacity.AddPoint(max_val, 0.6)
        
        self.gradientOpacity.RemoveAllPoints()
        self.gradientOpacity.AddPoint(0, 0.0)
        self.gradientOpacity.AddPoint(data_range * 0.1, 0.2)
        self.gradientOpacity.AddPoint(data_range * 0.3, 0.6)
        self.gradientOpacity.AddPoint(data_range * 0.5, 1.0)
        
        self.color.RemoveAllPoints()
        self.color.AddRGBPoint(min_val, 0.0, 0.0, 0.0)           # Black
        self.color.AddRGBPoint(low_thresh, 0.1, 0.1, 0.1)        # Dark gray
        self.color.AddRGBPoint(mid_low, 0.4, 0.4, 0.4)           # Gray
        self.color.AddRGBPoint(mid, 0.7, 0.7, 0.7)               # Light gray
        self.color.AddRGBPoint(mid_high, 0.9, 0.9, 0.9)          # Near white
        self.color.AddRGBPoint(max_val, 1.0, 1.0, 1.0)           # White
        
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(0.3)
        self.volumeProperty.SetDiffuse(0.7)
        self.volumeProperty.SetSpecular(0.2)
        self.volumeProperty.SetSpecularPower(10)
        
        # Use linear interpolation for smoother rendering
        self.volumeProperty.SetInterpolationTypeToLinear()

    def setup_auto_preset(self):
        """Automatically detect and setup best preset based on data characteristics."""
        if self.imageData is None:
            return
        
        scalar_range = self.imageData.GetScalarRange()
        min_val, max_val = scalar_range
        data_range = max_val - min_val
        
        print(f"Auto preset - Range: {min_val} to {max_val}, Span: {data_range}")
        
        # Detect if CT (typically -1000 to +3000 HU) or MRI (typically 0 to ~4000)
        is_ct = min_val < -500  # CT usually has negative values (air = -1000)
        
        if is_ct:
            print("Detected: CT data - using bone preset")
            self.setup_bone_preset()
        else:
            print("Detected: MRI/Other data - using adaptive preset")
            self._setup_adaptive_preset(min_val, max_val)
    
    def _setup_adaptive_preset(self, min_val, max_val):
        """Setup an adaptive preset based on actual data range."""
        data_range = max_val - min_val
        
        # Calculate adaptive thresholds
        p10 = min_val + data_range * 0.10
        p25 = min_val + data_range * 0.25
        p50 = min_val + data_range * 0.50
        p75 = min_val + data_range * 0.75
        p90 = min_val + data_range * 0.90
        
        self.scalarOpacity.RemoveAllPoints()
        self.scalarOpacity.AddPoint(min_val, 0.0)
        self.scalarOpacity.AddPoint(p10, 0.0)       # Cut background noise
        self.scalarOpacity.AddPoint(p25, 0.08)
        self.scalarOpacity.AddPoint(p50, 0.20)
        self.scalarOpacity.AddPoint(p75, 0.40)
        self.scalarOpacity.AddPoint(p90, 0.60)
        self.scalarOpacity.AddPoint(max_val, 0.70)
        
        self.gradientOpacity.RemoveAllPoints()
        self.gradientOpacity.AddPoint(0, 0.0)
        self.gradientOpacity.AddPoint(data_range * 0.05, 0.1)
        self.gradientOpacity.AddPoint(data_range * 0.2, 0.5)
        self.gradientOpacity.AddPoint(data_range * 0.4, 0.8)
        self.gradientOpacity.AddPoint(data_range, 1.0)
        
        # Grayscale color map
        self.color.RemoveAllPoints()
        self.color.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
        self.color.AddRGBPoint(p25, 0.3, 0.3, 0.3)
        self.color.AddRGBPoint(p50, 0.6, 0.6, 0.6)
        self.color.AddRGBPoint(p75, 0.85, 0.85, 0.85)
        self.color.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
        
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(0.2)
        self.volumeProperty.SetDiffuse(0.8)
        self.volumeProperty.SetSpecular(0.1)
        self.volumeProperty.SetInterpolationTypeToLinear()

    def _resample_image(self, image_data, max_size):
        """Resample image to fit within GPU texture limits."""
        dims = image_data.GetDimensions()
        max_dim = max(dims)
        scale_factor = max_size / max_dim
        
        resample = vtk.vtkImageResample()
        resample.SetInputData(image_data)
        resample.SetAxisMagnificationFactor(0, scale_factor)
        resample.SetAxisMagnificationFactor(1, scale_factor)
        resample.SetAxisMagnificationFactor(2, scale_factor)
        resample.SetInterpolationModeToLinear()
        resample.Update()
        
        result = vtk.vtkImageData()
        result.DeepCopy(resample.GetOutput())
        return result
    
    def setup_bone_preset(self):
        """Setup bone visualization preset."""
        self.scalarOpacity.RemoveAllPoints()
        self.scalarOpacity.AddPoint(-1000, 0.0)
        self.scalarOpacity.AddPoint(100, 0.0)
        self.scalarOpacity.AddPoint(400, 0.15)
        self.scalarOpacity.AddPoint(1000, 0.7)
        self.scalarOpacity.AddPoint(2000, 0.85)
        
        self.gradientOpacity.RemoveAllPoints()
        self.gradientOpacity.AddPoint(0, 0.0)
        self.gradientOpacity.AddPoint(90, 0.5)
        self.gradientOpacity.AddPoint(100, 1.0)
        
        self.color.RemoveAllPoints()
        self.color.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        self.color.AddRGBPoint(100, 0.55, 0.25, 0.15)
        self.color.AddRGBPoint(400, 0.88, 0.60, 0.40)
        self.color.AddRGBPoint(1000, 1.0, 0.94, 0.85)
        self.color.AddRGBPoint(2000, 1.0, 1.0, 0.95)
        
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
    
    def setup_soft_tissue_preset(self):
        """Setup soft tissue visualization preset."""
        # === ENHANCED VISIBILITY ===
        self.scalarOpacity.RemoveAllPoints()
        self.scalarOpacity.AddPoint(-1000, 0.0)
        self.scalarOpacity.AddPoint(-100, 0.0)   # Background/Air/Fat cutoff
        self.scalarOpacity.AddPoint(0, 0.35)     # 0 HU (Water/Tissue) - Increased from 0.1
        self.scalarOpacity.AddPoint(100, 0.65)   # 100 HU (Organs) - Increased from 0.3
        self.scalarOpacity.AddPoint(300, 0.85)   # 300 HU (Bone/Contrast) - Increased from 0.4
        
        # Add coloring to make it look "fleshy"
        self.color.RemoveAllPoints()
        self.color.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        self.color.AddRGBPoint(-100, 0.6, 0.4, 0.3)      # Skin tone start
        self.color.AddRGBPoint(0, 0.8, 0.5, 0.4)         # Muscle/Tissue
        self.color.AddRGBPoint(100, 0.9, 0.6, 0.5)       # Dense Organ
        self.color.AddRGBPoint(300, 1.0, 0.9, 0.8)       # Bone
        
        # Add gradient opacity to define surfaces better
        self.gradientOpacity.RemoveAllPoints()
        self.gradientOpacity.AddPoint(0, 0.0)
        self.gradientOpacity.AddPoint(20, 0.2)
        self.gradientOpacity.AddPoint(100, 1.0)
        
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(0.4)  # Brighter ambient
        self.volumeProperty.SetDiffuse(0.6)
        self.volumeProperty.SetSpecular(0.3)
        self.volumeProperty.SetSpecularPower(15)

    def setup_xray_preset(self):
        """Setup X-ray/CR visualization preset."""
        # Get scalar range for proper mapping
        if self.imageData:
            scalar_range = self.imageData.GetScalarRange()
            min_val, max_val = scalar_range
        else:
            min_val, max_val = 0, 4095
        
        self.scalarOpacity.RemoveAllPoints()
        self.scalarOpacity.AddPoint(min_val, 0.0)
        self.scalarOpacity.AddPoint(min_val + (max_val - min_val) * 0.1, 0.0)
        self.scalarOpacity.AddPoint(min_val + (max_val - min_val) * 0.3, 0.3)
        self.scalarOpacity.AddPoint(max_val, 0.8)
        
        self.gradientOpacity.RemoveAllPoints()
        self.gradientOpacity.AddPoint(0, 0.0)
        self.gradientOpacity.AddPoint(50, 0.5)
        self.gradientOpacity.AddPoint(100, 1.0)
        
        self.color.RemoveAllPoints()
        self.color.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
        self.color.AddRGBPoint(max_val * 0.5, 0.5, 0.5, 0.5)
        self.color.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
        
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
    
    def setup_muscle_preset(self):
        """Setup muscle visualization preset."""
        # === ENHANCED SEPARATION: MUSCLE vs SHELETAL ===
        self.scalarOpacity.RemoveAllPoints()
        self.scalarOpacity.AddPoint(-1000, 0.0)
        self.scalarOpacity.AddPoint(0, 0.0)
        self.scalarOpacity.AddPoint(20, 0.0)     # Cut fat/skin
        self.scalarOpacity.AddPoint(40, 0.4)     # Start of muscle
        self.scalarOpacity.AddPoint(80, 0.6)     # Peak muscle
        self.scalarOpacity.AddPoint(120, 0.3)    # Dip before bone
        self.scalarOpacity.AddPoint(300, 0.5)    # Bone starts
        self.scalarOpacity.AddPoint(1000, 0.8)   # Dense bone
        
        # Color: Red muscles, White bones
        self.color.RemoveAllPoints()
        self.color.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        self.color.AddRGBPoint(30, 0.6, 0.2, 0.2)        # Dark Red (Muscle start)
        self.color.AddRGBPoint(80, 0.9, 0.3, 0.3)        # Bright Red (Muscle peak)
        self.color.AddRGBPoint(150, 0.8, 0.6, 0.6)       # Transition
        self.color.AddRGBPoint(300, 0.95, 0.9, 0.8)      # Off-White (Bone)
        self.color.AddRGBPoint(1000, 1.0, 1.0, 1.0)      # White (Dense Bone)
        
        # Grading opacity for surface definition
        self.gradientOpacity.RemoveAllPoints()
        self.gradientOpacity.AddPoint(0, 0.0)
        self.gradientOpacity.AddPoint(50, 0.5)
        self.gradientOpacity.AddPoint(200, 1.0)
        
        self.volumeProperty.SetScalarOpacity(self.scalarOpacity)
        self.volumeProperty.SetGradientOpacity(self.gradientOpacity)
        self.volumeProperty.SetColor(self.color)
        self.volumeProperty.ShadeOn()
        self.volumeProperty.SetAmbient(0.3)
        self.volumeProperty.SetDiffuse(0.7)
        self.volumeProperty.SetSpecular(0.2)
    
    def clear(self):
        """Clear loaded data."""
        self.imageData = None
        self.is_loaded = False
        self.is_2d = False

class ViewportEventFilter(QObject):
    """Event filter to handle resize events for floating buttons."""
    def __init__(self, viewport_widget):
        super().__init__()
        self.viewport_widget = viewport_widget
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.viewport_widget._update_rotation_buttons_position()
        # Pass the event along
        return super().eventFilter(obj, event)

# ============================================================================
# VIEWPORT WIDGET
# ============================================================================

class ViewportWidget:
    """Individual viewport with renderer, camera, crosshairs, corner overlays, and measurement tools."""
    
    
    def __init__(self, parent, view_type, label_text, crosshair_manager=None):
        self.view_type = view_type
        self.label_text = label_text
        self.image_data_ref = None
        self.crosshair_manager = crosshair_manager
        
        # Create a container widget to hold VTK widget and overlay buttons
        self.container = QWidget(parent)
        self.container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        self.vtk_widget = QVTKRenderWindowInteractor(self.container)
        self.vtk_widget.setMinimumSize(300, 250)
        container_layout.addWidget(self.vtk_widget)
        
        # === RENDERER LAYERS SETUP ===
        # Layer 0: Main content (volume, slices)
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.0, 0.0, 0.0)
        self.renderer.SetLayer(0)
        
        # Layer 1: Overlay content (measurements)
        self.overlay_renderer = vtk.vtkRenderer()
        self.overlay_renderer.SetLayer(1)
        self.overlay_renderer.SetBackgroundAlpha(0.0) # Transparent
        self.overlay_renderer.InteractiveOff()
        
        # CRITICAL FIX FOR VISIBILITY:
        # PreserveColorBuffer(True) -> Keeps the volume visible underneath
        # PreserveDepthBuffer(False) -> Clears depth info so Layer 1 draws ON TOP of Layer 0
        self.overlay_renderer.SetPreserveColorBuffer(True)
        self.overlay_renderer.SetPreserveDepthBuffer(False)
        
        render_window = self.vtk_widget.GetRenderWindow()
        render_window.SetNumberOfLayers(2)
        render_window.AddRenderer(self.renderer)
        render_window.AddRenderer(self.overlay_renderer)
        
        if view_type == '3d':
            self.interactor_style = vtk.vtkInteractorStyleTrackballCamera()
        else:
            self.interactor_style = vtk.vtkInteractorStyleImage()
        
        self.vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(self.interactor_style)
        
        # Core rendering objects
        self.slice_mapper = None
        self.image_slice = None
        self.current_slice = 0
        self.max_slice = 0
        self.reslice = None
        self.slice_axis = 0
        self.volume = None
        self.volume_mapper = None  # Store reference to mapper for clipping
        self.axes_widget = None
        self.axes_actor = None
        self.initial_camera_state = None
        
        # Scale ruler actor (for 3D view)
        self.legend_scale_actor = None
        
        # Crosshair components
        self.crosshair_enabled = False
        self.crosshair_h_line = None
        self.crosshair_v_line = None
        self.crosshair_h_actor = None
        self.crosshair_v_actor = None
        self.crosshair_h_mapper = None
        self.crosshair_v_mapper = None
        
        # Image geometry info
        self.image_origin = [0, 0, 0]
        self.image_spacing = [1, 1, 1]
        self.image_dims = [1, 1, 1]
        
        # Measurement Tools -  SUPPORTS MULTIPLE MEASUREMENTS
        self.distance_widgets = []  # List of all distance widgets
        self.active_distance_widget = None  
        self.measurement_enabled = False
        self.measurement_unit = 'mm' 
        self.corner_annotation = None
        self.dicom_metadata = {}
        
        # Orientation labels actors
        self.orientation_actors = {}
        
        # === CLIPPING PLANE COMPONENTS ===
        self.clipping_plane = None
        self.clipping_plane_widget = None
        self.clipping_enabled = False
        
        # Floating rotation buttons (only for 3D view)
        self.rotation_buttons_widget = None
        self.event_filter = None  # Store event filter reference
        if view_type == '3d':
            self._setup_floating_rotation_buttons()
        
        # Setup static UI elements
        self._setup_corner_annotation()
        self._setup_crosshairs()
        
        # Setup scale rulers for 3D view
        if view_type == '3d':
            self._setup_scale_rulers()
        
        # Connect to crosshair manager
        if self.crosshair_manager and view_type != '3d':
            self.crosshair_manager.position_changed.connect(self._on_crosshair_position_changed)

    def _setup_scale_rulers(self):
        """Setup L-shaped scale rulers on the left and bottom edges of the 3D viewport."""
        try:
            # Create the legend scale actor
            self.legend_scale_actor = vtk.vtkLegendScaleActor()
            
            # === CONFIGURE L-SHAPE: Show only Left and Bottom axes ===
            # Hide Top and Right axes
            self.legend_scale_actor.TopAxisVisibilityOff()
            self.legend_scale_actor.RightAxisVisibilityOff()
            
            # Show Left and Bottom axes
            self.legend_scale_actor.LeftAxisVisibilityOn()
            self.legend_scale_actor.BottomAxisVisibilityOn()
            
            # Hide the legend (the small box showing scale info)
            self.legend_scale_actor.LegendVisibilityOff()
            
            # === STYLE: Yellow color to match reference ===
            # Get the axes and style them
            
            # Left Axis styling
            left_axis = self.legend_scale_actor.GetLeftAxis()
            if left_axis:
                # Set axis line color to yellow
                left_axis.GetProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
                left_axis.GetProperty().SetLineWidth(1.5)
                
                # Set label (numbers) color to yellow
                left_axis.GetLabelTextProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
                left_axis.GetLabelTextProperty().SetFontSize(12)
                left_axis.GetLabelTextProperty().SetFontFamilyToArial()
                left_axis.GetLabelTextProperty().BoldOff()
                left_axis.GetLabelTextProperty().ShadowOff()
                
                # Set title text property (if any)
                left_axis.GetTitleTextProperty().SetColor(1.0, 1.0, 0.0)
                left_axis.GetTitleTextProperty().SetFontSize(10)
            
            # Bottom Axis styling
            bottom_axis = self.legend_scale_actor.GetBottomAxis()
            if bottom_axis:
                # Set axis line color to yellow
                bottom_axis.GetProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
                bottom_axis.GetProperty().SetLineWidth(1.5)
                
                # Set label (numbers) color to yellow
                bottom_axis.GetLabelTextProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
                bottom_axis.GetLabelTextProperty().SetFontSize(12)
                bottom_axis.GetLabelTextProperty().SetFontFamilyToArial()
                bottom_axis.GetLabelTextProperty().BoldOff()
                bottom_axis.GetLabelTextProperty().ShadowOff()
                
                # Set title text property (if any)
                bottom_axis.GetTitleTextProperty().SetColor(1.0, 1.0, 0.0)
                bottom_axis.GetTitleTextProperty().SetFontSize(10)
            
            # Add to the main renderer (not overlay, as it needs to track camera)
            self.renderer.AddActor(self.legend_scale_actor)
            
            print("Scale rulers setup complete (L-shape, yellow)")
            
        except Exception as e:
            print(f"Warning: Could not setup scale rulers: {e}")
            import traceback
            traceback.print_exc()
            self.legend_scale_actor = None

    def set_scale_rulers_visible(self, visible):
        """Toggle scale rulers visibility."""
        if self.legend_scale_actor:
            self.legend_scale_actor.SetVisibility(visible)
            self.render()

    def _setup_floating_rotation_buttons(self):
        """Setup floating rotation buttons for 3D view."""
        # Create a widget to hold rotation buttons that floats over the VTK widget
        self.rotation_buttons_widget = QWidget(self.vtk_widget)
        self.rotation_buttons_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.rotation_buttons_widget.setAttribute(Qt.WA_TranslucentBackground, False)
        self.rotation_buttons_widget.setAutoFillBackground(True)
        self.rotation_buttons_widget.setStyleSheet("""
            QWidget {
                background-color: rgb(30, 30, 30);
                border-radius: 8px;
                border: 1px solid #3d3d3d;
            }
        """)
        # Increased height to 120 to fit all buttons
        self.rotation_buttons_widget.setFixedSize(110, 120)
        
        # Layout for rotation buttons
        rot_layout = QVBoxLayout(self.rotation_buttons_widget)
        rot_layout.setContentsMargins(8, 8, 8, 8)
        rot_layout.setSpacing(2)
        
        # Label
        rot_label = QLabel("3D Rotate")
        rot_label.setStyleSheet("color: #00bcd4; font-size: 10px; font-weight: bold; background: transparent; border: none;")
        rot_label.setAlignment(Qt.AlignCenter)
        rot_label.setFixedHeight(14)
        rot_layout.addWidget(rot_label)
        
        # Grid for buttons
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent; border: none;")
        btn_container.setFixedHeight(75)  # Fixed height for button grid
        rot_grid = QGridLayout(btn_container)
        rot_grid.setContentsMargins(0, 0, 0, 0)
        rot_grid.setSpacing(2)
        
        button_style = """
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00bcd4;
                color: black;
            }
            QPushButton:pressed {
                background-color: #008ba3;
            }
        """
        
        self.btn_rot_up = QPushButton("▲")
        self.btn_rot_up.setFixedSize(28, 22)
        self.btn_rot_up.setStyleSheet(button_style)
        rot_grid.addWidget(self.btn_rot_up, 0, 1, Qt.AlignCenter)
        
        self.btn_rot_left = QPushButton("◄")
        self.btn_rot_left.setFixedSize(28, 22)
        self.btn_rot_left.setStyleSheet(button_style)
        rot_grid.addWidget(self.btn_rot_left, 1, 0, Qt.AlignCenter)
        
        self.btn_rot_right = QPushButton("►")
        self.btn_rot_right.setFixedSize(28, 22)
        self.btn_rot_right.setStyleSheet(button_style)
        rot_grid.addWidget(self.btn_rot_right, 1, 2, Qt.AlignCenter)
        
        self.btn_rot_down = QPushButton("▼")
        self.btn_rot_down.setFixedSize(28, 22)
        self.btn_rot_down.setStyleSheet(button_style)
        rot_grid.addWidget(self.btn_rot_down, 2, 1, Qt.AlignCenter)
        
        rot_layout.addWidget(btn_container)
        
        # Install event filter using a proper QObject
        self.event_filter = ViewportEventFilter(self)
        self.vtk_widget.installEventFilter(self.event_filter)
        
        # Initial position
        self._update_rotation_buttons_position()

    def _update_rotation_buttons_position(self):
        """Update the position of floating rotation buttons."""
        if self.rotation_buttons_widget and self.vtk_widget:
            # Position above the scale rulers (moved up from bottom)
            x = 70
            # Move up by ~80 pixels to clear the scale ruler numbers
            y = self.vtk_widget.height() - self.rotation_buttons_widget.height() - 50
            self.rotation_buttons_widget.move(x, max(10, y))
            self.rotation_buttons_widget.raise_()
            self.rotation_buttons_widget.update()  # Force repaint


    def connect_rotation_buttons(self, rotate_callback):
        """Connect rotation buttons to a callback function."""
        if self.view_type == '3d' and self.rotation_buttons_widget:
            self.btn_rot_up.clicked.connect(lambda: rotate_callback('x', 15))
            self.btn_rot_down.clicked.connect(lambda: rotate_callback('x', -15))
            self.btn_rot_left.clicked.connect(lambda: rotate_callback('y', -15))
            self.btn_rot_right.clicked.connect(lambda: rotate_callback('y', 15))

    def _setup_corner_annotation(self):
        """Setup text overlays for 4 corners of the viewport."""
        self.corner_annotation = vtk.vtkCornerAnnotation()
        self.corner_annotation.SetMaximumFontSize(14)
        self.corner_annotation.SetMinimumFontSize(10)
        self.corner_annotation.GetTextProperty().SetColor(0.9, 0.9, 0.9)  # Light Grey
        self.corner_annotation.GetTextProperty().SetFontFamilyToArial()
        self.corner_annotation.SetLinearFontScaleFactor(2)
        self.corner_annotation.SetNonlinearFontScaleFactor(1)
        
        # Initial Text
        self.corner_annotation.SetText(0, "")  # Bottom Left (Technical: Slice, W/L)
        self.corner_annotation.SetText(1, "")  # Bottom Right
        self.corner_annotation.SetText(2, f"{self.label_text}")  # Top Left (View Name + Dims)
        self.corner_annotation.SetText(3, "")  # Top Right (Patient Info)
        
        self.renderer.AddViewProp(self.corner_annotation)

    def _setup_orientation_labels(self):
        """Setup orientation labels (L, R, A, P, S, I) on the edges of 2D views."""
        if self.view_type == '3d':
            return
        
        orientation_map = {
            'axial': ('R', 'L', 'A', 'P'),
            'sagittal': ('A', 'P', 'S', 'I'),
            'coronal': ('R', 'L', 'S', 'I')
        }
        
        labels = orientation_map.get(self.view_type, ('', '', '', ''))
        positions = {
            'left': (0.02, 0.5),
            'right': (0.98, 0.5),
            'top': (0.5, 0.98),
            'bottom': (0.5, 0.02)
        }
        
        label_names = ['left', 'right', 'top', 'bottom']
        
        for i, (pos_name, label_text) in enumerate(zip(label_names, labels)):
            if label_text:
                text_actor = vtk.vtkTextActor()
                text_actor.SetInput(label_text)
                text_actor.GetTextProperty().SetFontSize(16)
                text_actor.GetTextProperty().SetColor(1.0, 0.8, 0.0)
                text_actor.GetTextProperty().SetFontFamilyToArial()
                text_actor.GetTextProperty().BoldOn()
                text_actor.GetTextProperty().SetJustificationToCentered()
                text_actor.GetTextProperty().SetVerticalJustificationToCentered()
                
                coord = text_actor.GetPositionCoordinate()
                coord.SetCoordinateSystemToNormalizedViewport()
                coord.SetValue(positions[pos_name][0], positions[pos_name][1])
                
                self.renderer.AddActor2D(text_actor)
                self.orientation_actors[pos_name] = text_actor

    def update_metadata_overlay(self, metadata=None):
        """Update the corner text with real DICOM data."""
        if metadata:
            self.dicom_metadata = metadata
        
        if self.corner_annotation is None:
            return

        name = self.dicom_metadata.get('patient_name', 'Anonymous')
        modality = self.dicom_metadata.get('modality', '')
        date = self.dicom_metadata.get('study_date', '')
        
        if date and len(date) == 8:
            date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
        
        top_right = f"{name}\n{modality}\n{date}"
        self.corner_annotation.SetText(3, top_right)
        
        if self.image_data_ref:
            dims = self.image_data_ref.GetDimensions()
            top_left = f"{self.label_text}\n{dims[0]} x {dims[1]}"
        else:
            top_left = f"{self.label_text}"
        self.corner_annotation.SetText(2, top_left)
        
        self._update_slice_text()

    def _create_new_distance_widget(self):
        """Create a distance widget that renders in the overlay layer and stays visible."""
        distance_widget = vtk.vtkDistanceWidget()
        interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        distance_widget.SetInteractor(interactor)
    
        # Drive the widget from the overlay renderer so it draws above the volume/slices
        distance_widget.SetDefaultRenderer(self.overlay_renderer)
        distance_widget.SetCurrentRenderer(self.overlay_renderer)
    
        # Representation by view type
        if self.view_type == '3d':
            rep = vtk.vtkDistanceRepresentation3D()
            distance_widget.SetRepresentation(rep)
            
            # === ENHANCED VISIBILITY FOR 3D ===
            try:
                # Line styling - thicker yellow line
                rep.GetLineProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
                rep.GetLineProperty().SetLineWidth(4.0)
                rep.GetLineProperty().SetOpacity(1.0)
                
                # Label scaling - MUCH LARGER
                rep.SetLabelScale(8.0, 8.0, 8.0)  # Increased from 4.0
                
                # Glyph (endpoint markers) styling
                glyph = rep.GetGlyphActor()
                if glyph:
                    glyph.GetProperty().SetColor(0.0, 1.0, 1.0)  # Cyan
                    glyph.GetProperty().SetOpacity(1.0)
                    glyph.GetProperty().SetPointSize(12.0)
                
                # For 3D representation, the label is a 3D text actor
                # We need to access it differently - use GetLabelActor() if available
                # or style through the representation's label format
                label_actor = rep.GetLabelActor()
                if label_actor and hasattr(label_actor, 'GetTextProperty'):
                    label_prop = label_actor.GetTextProperty()
                    if label_prop:
                        label_prop.SetColor(1.0, 1.0, 0.0)  # Yellow
                        label_prop.SetFontSize(24)  # Larger font
                        label_prop.BoldOn()
                        label_prop.SetFontFamilyToArial()
                        label_prop.ShadowOn()
                        label_prop.SetShadowOffset(2, 2)
                    
            except Exception as e:
                print(f"3D rep styling error: {e}")
                
            # Picker for snapping on volume
            self._setup_volume_picker_for_widget(distance_widget)
        else:
            # ...existing code for 2D...
            rep = vtk.vtkDistanceRepresentation2D()
            distance_widget.SetRepresentation(rep)
            
            # === ENHANCED VISIBILITY FOR 2D ===
            try:
                # Axis (line) styling
                axis_prop = rep.GetAxisProperty()
                if axis_prop:
                    axis_prop.SetColor(1.0, 1.0, 0.0)  # Yellow
                    axis_prop.SetLineWidth(3.0)
                    axis_prop.SetOpacity(1.0)
                
                # Axis label styling
                axis = rep.GetAxis()
                if axis:
                    # Title text (the measurement value)
                    tprop = axis.GetTitleTextProperty()
                    if tprop:
                        tprop.SetColor(1.0, 1.0, 0.0)  # Yellow
                        tprop.SetFontSize(20)  # Larger font
                        tprop.BoldOn()
                        tprop.SetFontFamilyToArial()
                        tprop.ShadowOn()
                    
                    # Label text property
                    lprop = axis.GetLabelTextProperty()
                    if lprop:
                        lprop.SetColor(1.0, 1.0, 0.0)
                        lprop.SetFontSize(18)
                        lprop.BoldOn()
                        
            except Exception as e:
                print(f"2D rep styling error: {e}")
    
        # Ensure the representation renders in the overlay layer
        if hasattr(rep, "SetRenderer"):
            rep.SetRenderer(self.overlay_renderer)
    
        # Label format based on current unit
        self._force_update_label(distance_widget)
    
        # Interaction hooks
        def on_interaction(obj, event):
            if self.view_type == '3d':
                self._snap_measurement_to_surface_live(distance_widget)
            self._force_update_label(distance_widget)
            self.render()
    
        def on_end_interaction(obj, event):
            if self.measurement_enabled:
                self._on_measurement_complete(distance_widget)
            self._force_update_label(distance_widget)
            self.render()
    
        distance_widget.AddObserver("InteractionEvent", on_interaction)
        distance_widget.AddObserver("EndInteractionEvent", on_end_interaction)
    
        return distance_widget

    def _setup_volume_picker_for_widget(self, widget):
        """Setup volume picker for the distance widget in 3D view."""
        try:
            # vtkVolumePicker is best for "visual" surface picking on volumes
            picker = vtk.vtkVolumePicker()
            picker.SetTolerance(0.001)
            picker.PickFromListOn()
            if self.volume:
                picker.AddPickList(self.volume)
            
            # Set this picker on the interactor so the FIRST click uses it
            interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
            interactor.SetPicker(picker)
            
            # Store for manual snapping during drag
            self._volume_picker = picker
        except Exception as e:
            print(f"Error setting up volume picker: {e}")
        
    def _snap_measurement_to_surface_live(self, widget):
        """Snap the currently moving handle to the volume surface using mouse position."""
        if not hasattr(self, '_volume_picker') or self._volume_picker is None:
            return
        if self.volume is None:
            return
            
        try:
            rep = widget.GetRepresentation()
            
            # Get widget state: Start=0, Define=1, Manipulate=2
            widget_state = widget.GetWidgetState()
            
            # Get interaction state: Outside=0, NearP1=1, NearP2=2
            interaction_state = rep.GetInteractionState()
            
            point_to_snap = 0 # 0=None, 1=P1, 2=P2
            
            # Logic to determine which point is moving
            if widget_state == 1: 
                # We are in "Define" mode (dragging to place the 2nd point)
                point_to_snap = 2
            elif interaction_state == 1: 
                point_to_snap = 1
            elif interaction_state == 2: 
                point_to_snap = 2
            
            if point_to_snap == 0:
                return

            interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
            event_pos = interactor.GetEventPosition()
            
            picker = self._volume_picker
            
            # Perform the pick at the current mouse position
            if picker.Pick(event_pos[0], event_pos[1], 0, self.renderer):
                pos = picker.GetPickPosition()
                
                # Update the position of the handle being moved
                if point_to_snap == 1:
                    rep.SetPoint1WorldPosition(pos)
                elif point_to_snap == 2:
                    rep.SetPoint2WorldPosition(pos)
                
                # Force the representation to update
                rep.BuildRepresentation()
        except Exception as e:
            pass
            
    def _get_mm_to_pixel_factor(self):
        """Get the conversion factor from mm to pixels."""
        if self.image_data_ref is not None:
            spacing = self.image_data_ref.GetSpacing()
            # Average of X and Y spacing (mm per pixel)
            avg_spacing = (spacing[0] + spacing[1]) / 2.0
            if avg_spacing > 0:
                return 1.0 / avg_spacing  # pixels per mm
        return 1.0

    def _force_update_label(self, widget):
        """Force update the label with correct unit conversion."""
        if widget is None:
            return
        
        representation = widget.GetRepresentation()
        if representation is None:
            return
        
        # Get the world distance (in mm)
        distance_mm = representation.GetDistance()
        
        if self.measurement_unit == 'px':
            # Convert to pixels
            px_per_mm = self._get_mm_to_pixel_factor()
            distance_px = distance_mm * px_per_mm
            # Set format string with the calculated pixel value embedded
            representation.SetLabelFormat(f"{distance_px:.2f} px")
        else:
            representation.SetLabelFormat("%-#6.2f mm")



    def _on_measurement_complete(self, completed_widget):
        """Called when a measurement is completed."""
        # === FIX: PREVENT BLUE DOTS (Zero-length measurements) ===
        rep = completed_widget.GetRepresentation()
        p1 = [0.0, 0.0, 0.0]
        p2 = [0.0, 0.0, 0.0]
        rep.GetPoint1WorldPosition(p1)
        rep.GetPoint2WorldPosition(p2)
        
        # Calculate distance squared
        dist_sq = sum((p1[i] - p2[i])**2 for i in range(3))
        
        # If distance is tiny (accidental click), delete the widget
        if dist_sq < 0.001:
            completed_widget.Off()
            completed_widget.SetInteractor(None)
            # Don't add to list, just return
            # But we still need to reactivate the tool if enabled
            if self.measurement_enabled:
                # Reuse the active widget slot if possible, or create new
                if self.active_distance_widget == completed_widget:
                     # It was the active one, just reset it? 
                     # Easier to just let it die and make a new one
                     pass
                self.active_distance_widget = self._create_new_distance_widget()
                self.active_distance_widget.On()
            self.render()
            return

        # Add to our list if not already there
        if completed_widget not in self.distance_widgets:
            self.distance_widgets.append(completed_widget)
        
        # Create a new widget for the next measurement
        if self.measurement_enabled:
            self.active_distance_widget = self._create_new_distance_widget()
            self.active_distance_widget.On()
        
        self.render()

    def set_measurement_unit(self, unit):
        """Set the measurement unit ('mm' or 'px') and update all labels."""
        self.measurement_unit = unit
        
        # Update all existing distance widgets
        for widget in self.distance_widgets:
            self._force_update_label(widget)
        
        # Update active widget if exists  
        if self.active_distance_widget:
            self._force_update_label(self.active_distance_widget)
        
        self.render()

    def get_measurement_distances(self):
        """Get all measurement distances in both mm and pixels."""
        measurements = []
        px_per_mm = self._get_mm_to_pixel_factor()
        
        for widget in self.distance_widgets:
            rep = widget.GetRepresentation()
            if rep:
                distance_mm = rep.GetDistance()
                distance_px = distance_mm * px_per_mm
                
                measurements.append({
                    'mm': distance_mm,
                    'px': distance_px
                })
        
        return measurements

    def set_measurement_enabled(self, enabled):
        """Toggle the ruler tool mode."""
        self.measurement_enabled = enabled
        
        if enabled:
            # Create initial distance widget if none exists
            if self.active_distance_widget is None:
                self.active_distance_widget = self._create_new_distance_widget()
            self.active_distance_widget.On()
            
            # Enable interaction on all existing widgets
            for widget in self.distance_widgets:
                widget.On()
                widget.ProcessEventsOn()
        else:
            # Turn off active widget
            if self.active_distance_widget:
                self.active_distance_widget.Off()
            
            # Keep existing measurements visible but not interactive
            for widget in self.distance_widgets:
                # Keep widget ON for visibility, but disable interaction
                widget.ProcessEventsOff()
        
        self.render()

    def clear_all_measurements(self):
        """Clear all measurement rulers from the viewport."""
        # Remove all distance widgets
        for widget in self.distance_widgets:
            widget.Off()
            widget.SetInteractor(None)
        self.distance_widgets.clear()
        
        # Reset active widget
        if self.active_distance_widget:
            self.active_distance_widget.Off()
            self.active_distance_widget.SetInteractor(None)
            self.active_distance_widget = None
        
        # Create new active widget if measurement is enabled
        if self.measurement_enabled:
            self.active_distance_widget = self._create_new_distance_widget()
            self.active_distance_widget.On()
        
        self.render()

    def clear_last_measurement(self):
        """Clear only the last measurement ruler."""
        if self.distance_widgets:
            last_widget = self.distance_widgets.pop()
            last_widget.Off()
            last_widget.SetInteractor(None)
            self.render()

    def get_measurement_count(self):
        """Return the number of measurements in this viewport."""
        return len(self.distance_widgets)

     # --- ADD THESE METHODS ---
    def get_measurements_data(self):
        """Extract measurement points for saving."""
        data = []
        for widget in self.distance_widgets:
            rep = widget.GetRepresentation()
            p1 = [0.0, 0.0, 0.0]
            p2 = [0.0, 0.0, 0.0]
            rep.GetPoint1WorldPosition(p1)
            rep.GetPoint2WorldPosition(p2)
            data.append({'p1': list(p1), 'p2': list(p2)})
        return data

    def restore_measurements(self, data_list):
        """Restore measurements from saved data and make them visible again."""
        # 1) Remove any existing widgets
        for widget in self.distance_widgets:
            widget.Off()
            widget.SetInteractor(None)
        self.distance_widgets.clear()

        if self.active_distance_widget:
            self.active_distance_widget.Off()
            self.active_distance_widget.SetInteractor(None)
            self.active_distance_widget = None

        # 2) Make sure overlay and main renderer share the same camera
        if hasattr(self, "overlay_renderer") and hasattr(self, "renderer"):
            self.overlay_renderer.SetActiveCamera(self.renderer.GetActiveCamera())

        # 3) Recreate widgets from saved points
        for item in data_list:
            p1 = item.get('p1', [0, 0, 0])
            p2 = item.get('p2', [0, 0, 0])
            
            # Calculate the distance for the label
            distance = ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2) ** 0.5

            # --- Create a simple line actor for guaranteed visibility ---
            try:
                line = vtk.vtkLineSource()
                line.SetPoint1(p1)
                line.SetPoint2(p2)
                line.Update()

                line_mapper = vtk.vtkPolyDataMapper()
                line_mapper.SetInputConnection(line.GetOutputPort())

                line_actor = vtk.vtkActor()
                line_actor.SetMapper(line_mapper)
                line_actor.GetProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
                line_actor.GetProperty().SetLineWidth(4.0)  # Thicker line

                self.overlay_renderer.AddActor(line_actor)
            except Exception as e:
                print(f"Error creating measurement line: {e}")

            # --- Create a LARGER text label for the distance ---
            try:
                # Calculate midpoint for label position
                mid_point = [
                    (p1[0] + p2[0]) / 2.0,
                    (p1[1] + p2[1]) / 2.0,
                    (p1[2] + p2[2]) / 2.0
                ]
                
                # Format distance based on current unit
                if self.measurement_unit == 'px':
                    px_per_mm = self._get_mm_to_pixel_factor()
                    distance_display = distance * px_per_mm
                    label_text = f"{distance_display:.2f} px"
                else:
                    label_text = f"{distance:.2f} mm"
                
                # Create 3D text actor for label - MUCH LARGER AND MORE VISIBLE
                text_actor = vtk.vtkBillboardTextActor3D()
                text_actor.SetInput(label_text)
                text_actor.SetPosition(mid_point)
                
                # === ENHANCED TEXT VISIBILITY ===
                text_prop = text_actor.GetTextProperty()
                text_prop.SetFontSize(24)  # Larger font size
                text_prop.SetColor(1.0, 1.0, 0.0)  # Yellow
                text_prop.SetBold(True)
                text_prop.SetFontFamilyToArial()
                text_prop.SetJustificationToCentered()
                text_prop.SetVerticalJustificationToCentered()
                
                # Add background for better readability
                text_prop.SetBackgroundColor(0.0, 0.0, 0.0)  # Black background
                text_prop.SetBackgroundOpacity(0.7)  # More opaque background
                text_prop.SetFrameColor(1.0, 1.0, 0.0)  # Yellow frame
                text_prop.FrameOn()
                text_prop.SetFrameWidth(2)
                
                # Shadow for depth
                text_prop.ShadowOn()
                text_prop.SetShadowOffset(2, -2)
                
                self.overlay_renderer.AddActor(text_actor)
            except Exception as e:
                print(f"Error creating measurement label: {e}")

            # --- Also create the widget for potential future interaction ---
            widget = self._create_new_distance_widget()
            rep = widget.GetRepresentation()

            if hasattr(rep, "SetRenderer"):
                rep.SetRenderer(self.overlay_renderer)

            widget.On()
            rep.SetPoint1WorldPosition(p1)
            rep.SetPoint2WorldPosition(p2)

            if hasattr(widget, 'SetWidgetState'):
                widget.SetWidgetState(2)  # Manipulate state
            
            if hasattr(rep, 'BuildRepresentation'):
                rep.BuildRepresentation()

            # Force label update
            self._force_update_label(widget)
            
            self.distance_widgets.append(widget)

        # 4) Update overlay renderer + viewport
        if hasattr(self, "overlay_renderer"):
            self.overlay_renderer.ResetCameraClippingRange()
            self.overlay_renderer.Modified()

        self.render()

    def _update_slice_text(self):
        """Update Bottom-Left text with Slice #, Zoom, and Window/Level."""
        if self.corner_annotation is None:
            return
        
        parts = []
        
        if self.max_slice > 0:
            parts.append(f"Slice: {self.current_slice + 1}/{self.max_slice + 1}")
        
        if self.image_slice:
            prop = self.image_slice.GetProperty()
            ww = prop.GetColorWindow()
            wl = prop.GetColorLevel()
            parts.append(f"W: {int(ww)} L: {int(wl)}")
        
        cam = self.renderer.GetActiveCamera()
        if cam and cam.GetParallelProjection():
            scale = cam.GetParallelScale()
            if scale > 0:
                zoom = 100.0 / scale
                parts.append(f"Zoom: {zoom:.0f}%")
        
        # Add measurement count if any
        if self.distance_widgets:
            parts.append(f"Measurements: {len(self.distance_widgets)}")
        
        bottom_left = "\n".join(parts)
        self.corner_annotation.SetText(0, bottom_left)

    def _setup_crosshairs(self):
        """Setup crosshair line actors (initially hidden)."""
        if self.view_type == '3d':
            return
        
        self.crosshair_h_line = vtk.vtkLineSource()
        self.crosshair_h_line.SetPoint1(0, 0, 0)
        self.crosshair_h_line.SetPoint2(1, 0, 0)
        
        self.crosshair_h_mapper = vtk.vtkPolyDataMapper()
        self.crosshair_h_mapper.SetInputConnection(self.crosshair_h_line.GetOutputPort())
        
        self.crosshair_h_actor = vtk.vtkActor()
        self.crosshair_h_actor.SetMapper(self.crosshair_h_mapper)
        self.crosshair_h_actor.GetProperty().SetColor(1.0, 1.0, 0.0)
        self.crosshair_h_actor.GetProperty().SetLineWidth(2.0)
        self.crosshair_h_actor.SetVisibility(False)
        self.crosshair_h_actor.GetProperty().SetOpacity(0.8)
        
        self.crosshair_v_line = vtk.vtkLineSource()
        self.crosshair_v_line.SetPoint1(0, 0, 0)
        self.crosshair_v_line.SetPoint2(0, 1, 0)
        
        self.crosshair_v_mapper = vtk.vtkPolyDataMapper()
        self.crosshair_v_mapper.SetInputConnection(self.crosshair_v_line.GetOutputPort())
        
        self.crosshair_v_actor = vtk.vtkActor()
        self.crosshair_v_actor.SetMapper(self.crosshair_v_mapper)
        self.crosshair_v_actor.GetProperty().SetColor(1.0, 1.0, 0.0)
        self.crosshair_v_actor.GetProperty().SetLineWidth(2.0)
        self.crosshair_v_actor.SetVisibility(False)
        self.crosshair_v_actor.GetProperty().SetOpacity(0.8)

    def _add_crosshairs_to_renderer(self):
        """Add crosshair actors to renderer (call after image is added)."""
        if self.view_type == '3d':
            return
        
        if self.crosshair_h_actor is None:
            self._setup_crosshairs()
        
        if self.crosshair_h_actor:
            actors = self.renderer.GetActors()
            actors.InitTraversal()
            found_h = False
            found_v = False
            for i in range(actors.GetNumberOfItems()):
                actor = actors.GetNextActor()
                if actor == self.crosshair_h_actor:
                    found_h = True
                if actor == self.crosshair_v_actor:
                    found_v = True
            
            if not found_h:
                self.renderer.AddActor(self.crosshair_h_actor)
            if not found_v:
                self.renderer.AddActor(self.crosshair_v_actor)

    def set_crosshair_enabled(self, enabled):
        """Enable or disable crosshair display and synchronization."""
        self.crosshair_enabled = enabled
        
        if self.view_type == '3d':
            return
        
        if self.crosshair_h_actor is None:
            self._setup_crosshairs()
        
        self._add_crosshairs_to_renderer()
        
        if self.crosshair_h_actor:
            self.crosshair_h_actor.SetVisibility(enabled)
        if self.crosshair_v_actor:
            self.crosshair_v_actor.SetVisibility(enabled)
        
        if enabled and self.crosshair_manager and self.image_data_ref:
            x, y, z = self.crosshair_manager.current_center
            self._update_crosshair_lines(x, y, z)
        
        self.render()

    def _update_crosshair_lines(self, x, y, z):
        """Update crosshair line positions based on world coordinates."""
        if self.view_type == '3d' or not self.crosshair_enabled:
            return
        
        if self.image_data_ref is None or self.reslice is None:
            return
        
        bounds = self.image_data_ref.GetBounds()
        origin = self.image_data_ref.GetOrigin()
        spacing = self.image_data_ref.GetSpacing()
        dims = self.image_data_ref.GetDimensions()
        
        self.reslice.Update()
        reslice_output = self.reslice.GetOutput()
        if reslice_output is None:
            return
        
        reslice_bounds = reslice_output.GetBounds()
        reslice_origin = reslice_output.GetOrigin()
        reslice_spacing = reslice_output.GetSpacing()
        reslice_dims = reslice_output.GetDimensions()
        
        if self.view_type == 'axial':
            px = (x - origin[0]) / spacing[0] if spacing[0] != 0 else 0
            py = (y - origin[1]) / spacing[1] if spacing[1] != 0 else 0
            
            rx = reslice_origin[0] + px * reslice_spacing[0]
            ry = reslice_origin[1] + py * reslice_spacing[1]
            rz = reslice_origin[2]
            
            x_min = reslice_origin[0]
            x_max = reslice_origin[0] + (reslice_dims[0] - 1) * reslice_spacing[0]
            y_min = reslice_origin[1]
            y_max = reslice_origin[1] + (reslice_dims[1] - 1) * reslice_spacing[1]
            
            self.crosshair_v_line.SetPoint1(rx, y_min, rz)
            self.crosshair_v_line.SetPoint2(rx, y_max, rz)
            self.crosshair_h_line.SetPoint1(x_min, ry, rz)
            self.crosshair_h_line.SetPoint2(x_max, ry, rz)
            
        elif self.view_type == 'sagittal':
            py = (y - origin[1]) / spacing[1] if spacing[1] != 0 else 0
            pz = (z - origin[2]) / spacing[2] if spacing[2] != 0 else 0
            
            rx = reslice_origin[0] + pz * reslice_spacing[0]
            ry = reslice_origin[1] + py * reslice_spacing[1]
            rz = reslice_origin[2]
            
            x_min = reslice_origin[0]
            x_max = reslice_origin[0] + (reslice_dims[0] - 1) * reslice_spacing[0]
            y_min = reslice_origin[1]
            y_max = reslice_origin[1] + (reslice_dims[1] - 1) * reslice_spacing[1]
            
            self.crosshair_v_line.SetPoint1(rx, y_min, rz)
            self.crosshair_v_line.SetPoint2(rx, y_max, rz)
            self.crosshair_h_line.SetPoint1(x_min, ry, rz)
            self.crosshair_h_line.SetPoint2(x_max, ry, rz)
            
        elif self.view_type == 'coronal':
            px = (x - origin[0]) / spacing[0] if spacing[0] != 0 else 0
            pz = (z - origin[2]) / spacing[2] if spacing[2] != 0 else 0
            
            rx = reslice_origin[0] + px * reslice_spacing[0]
            ry = reslice_origin[1] + pz * reslice_spacing[1]
            rz = reslice_origin[2]
            
            x_min = reslice_origin[0]
            x_max = reslice_origin[0] + (reslice_dims[0] - 1) * reslice_spacing[0]
            y_min = reslice_origin[1]
            y_max = reslice_origin[1] + (reslice_dims[1] - 1) * reslice_spacing[1]
            
            self.crosshair_v_line.SetPoint1(rx, y_min, rz)
            self.crosshair_v_line.SetPoint2(rx, y_max, rz)
            self.crosshair_h_line.SetPoint1(x_min, ry, rz)
            self.crosshair_h_line.SetPoint2(x_max, ry, rz)

    def _on_crosshair_position_changed(self, x, y, z):
        """Handle crosshair position change from manager."""
        if not self.crosshair_enabled or self.view_type == '3d':
            return
        
        if self.image_data_ref is None:
            return
        
        self._update_reslice_from_world_position(x, y, z)
        self._update_crosshair_lines(x, y, z)
        self._update_slice_text()
        self.render()

    def _update_reslice_from_world_position(self, x, y, z):
        """Update reslice origin based on world position."""
        if self.reslice is None or self.image_data_ref is None:
            return
        
        origin = self.image_data_ref.GetOrigin()
        spacing = self.image_data_ref.GetSpacing()
        dims = self.image_data_ref.GetDimensions()
        
        if self.view_type == 'axial':
            self.current_slice = int(round((z - origin[2]) / spacing[2]))
            self.current_slice = max(0, min(self.current_slice, dims[2] - 1))
            self.reslice.SetResliceAxesOrigin(origin[0], origin[1], z)
            
        elif self.view_type == 'sagittal':
            self.current_slice = int(round((x - origin[0]) / spacing[0]))
            self.current_slice = max(0, min(self.current_slice, dims[0] - 1))
            self.reslice.SetResliceAxesOrigin(x, origin[1], origin[2])
            
        elif self.view_type == 'coronal':
            self.current_slice = int(round((y - origin[1]) / spacing[1]))
            self.current_slice = max(0, min(self.current_slice, dims[1] - 1))
            self.reslice.SetResliceAxesOrigin(origin[0], y, origin[2])
        
        self.reslice.Update()

    
    def _setup_coordinate_axes(self):
        """Setup anatomical orientation cube in the corner (replaces simple XYZ arrows)."""
        try:
            # Create the annotated cube actor with anatomical labels
            self.cube_actor = vtk.vtkAnnotatedCubeActor()
            
            # Set anatomical orientation labels
            self.cube_actor.SetXPlusFaceText("R")   # Right
            self.cube_actor.SetXMinusFaceText("L")  # Left
            self.cube_actor.SetYPlusFaceText("A")   # Anterior
            self.cube_actor.SetYMinusFaceText("P")  # Posterior
            self.cube_actor.SetZPlusFaceText("S")   # Superior
            self.cube_actor.SetZMinusFaceText("I")  # Inferior
            
            # Configure cube appearance - DARK cube body to match UI theme
            self.cube_actor.SetFaceTextScale(0.65)  # Larger text relative to face
            self.cube_actor.GetCubeProperty().SetColor(0.15, 0.15, 0.18)  # Dark gray matching #1e1e1e
            self.cube_actor.GetCubeProperty().SetOpacity(1.0)
            
            # Style the text on each face with BRIGHT colors for visibility on dark background
            # X-axis (Left/Right): Bright Red
            self.cube_actor.GetXPlusFaceProperty().SetColor(1.0, 0.4, 0.4)   # R - Light Red
            self.cube_actor.GetXMinusFaceProperty().SetColor(1.0, 0.4, 0.4)  # L - Light Red
            
            # Y-axis (Anterior/Posterior): Bright Green
            self.cube_actor.GetYPlusFaceProperty().SetColor(0.4, 1.0, 0.4)   # A - Light Green
            self.cube_actor.GetYMinusFaceProperty().SetColor(0.4, 1.0, 0.4)  # P - Light Green
            
            # Z-axis (Superior/Inferior): Cyan (theme color #00bcd4)
            self.cube_actor.GetZPlusFaceProperty().SetColor(0.0, 0.74, 0.83)  # S - Cyan
            self.cube_actor.GetZMinusFaceProperty().SetColor(0.0, 0.74, 0.83) # I - Cyan
            
            # Add XYZ axes arrows to the cube
            axes = vtk.vtkAxesActor()
            axes.SetShaftTypeToCylinder()
            axes.SetCylinderRadius(0.05)
            axes.SetTotalLength(1.5, 1.5, 1.5)  # Length of each axis
            
            # Configure axis labels
            axes.SetXAxisLabelText("X")
            axes.SetYAxisLabelText("Y")
            axes.SetZAxisLabelText("Z")
            
            # Style the axis label text
            axes.GetXAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
            axes.GetYAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
            axes.GetZAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
            
            axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(12)
            axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(12)
            axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(12)
            
            axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetColor(1, 0.3, 0.3)  # Red
            axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0.3, 1, 0.3)  # Green
            axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetColor(0, 0.74, 0.83)  # Cyan
            
            axes.GetXAxisCaptionActor2D().GetCaptionTextProperty().ShadowOff()
            axes.GetYAxisCaptionActor2D().GetCaptionTextProperty().ShadowOff()
            axes.GetZAxisCaptionActor2D().GetCaptionTextProperty().ShadowOff()
            
            # Combine cube and axes into a single assembly
            self.orientation_assembly = vtk.vtkPropAssembly()
            self.orientation_assembly.AddPart(self.cube_actor)
            self.orientation_assembly.AddPart(axes)
            
            # Create the orientation marker widget
            self.axes_widget = vtk.vtkOrientationMarkerWidget()
            self.axes_widget.SetOrientationMarker(self.orientation_assembly)
            
            # Position in bottom-right corner - make it larger
            # SetViewport(xmin, ymin, xmax, ymax) in normalized coordinates
            self.axes_widget.SetViewport(0.75, 0.0, 1.0, 0.28)
            
            # Keep reference to old axes_actor name for compatibility
            self.axes_actor = self.cube_actor
            
        except Exception as e:
            print(f"Warning: Could not setup orientation cube: {e}")
            import traceback
            traceback.print_exc()
            self.axes_widget = None
            self.cube_actor = None
    
    def _enable_axes_widget(self):
        """Enable the axes widget after interactor is initialized."""
        try:
            if self.axes_widget is None:
                self._setup_coordinate_axes()
            
            if self.axes_widget:
                interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
                if interactor:
                    self.axes_widget.SetInteractor(interactor)
                    self.axes_widget.SetEnabled(1)
                    self.axes_widget.InteractiveOff()
        except Exception as e:
            print(f"Warning: Could not enable axes widget: {e}")

    def setup_2d_view(self, image_data, orientation):
        """Setup 2D slice view (Axial, Sagittal, Coronal)."""
        if image_data is None:
            print(f"ERROR: No image data for {orientation} view")
            return
        
        try:
            self.image_data_ref = image_data
            dims = image_data.GetDimensions()
            self.image_dims = list(dims)
            self.image_origin = list(image_data.GetOrigin())
            self.image_spacing = list(image_data.GetSpacing())
            
            print(f"Setting up {orientation} view with dims: {dims}")
            
            self.reslice = vtk.vtkImageReslice()
            self.reslice.SetInputData(image_data)
            self.reslice.SetOutputDimensionality(2)
            self.reslice.SetInterpolationModeToLinear()
            
            if orientation == 'axial':
                self.reslice.SetResliceAxesDirectionCosines(1, 0, 0, 0, 1, 0, 0, 0, 1)
                self.max_slice = max(0, dims[2] - 1)
                self.slice_axis = 2
            elif orientation == 'sagittal':
                self.reslice.SetResliceAxesDirectionCosines(0, 0, 1, 0, 1, 0, 1, 0, 0)
                self.max_slice = max(0, dims[0] - 1)
                self.slice_axis = 0
            elif orientation == 'coronal':
                self.reslice.SetResliceAxesDirectionCosines(1, 0, 0, 0, 0, 1, 0, 1, 0)
                self.max_slice = max(0, dims[1] - 1)
                self.slice_axis = 1
            
            self.current_slice = self.max_slice // 2
            self._update_slice_position(image_data)
            self.reslice.Update()
            
            self.slice_mapper = vtk.vtkImageSliceMapper()
            self.slice_mapper.SetInputConnection(self.reslice.GetOutputPort())
            
            self.image_slice = vtk.vtkImageSlice()
            self.image_slice.SetMapper(self.slice_mapper)
            
            prop = self.image_slice.GetProperty()
            
            scalar_range = image_data.GetScalarRange()
            min_val, max_val = scalar_range
            
            auto_window = max_val - min_val
            auto_level = (max_val + min_val) / 2.0
            
            if auto_window > 0:
                prop.SetColorWindow(auto_window)
                prop.SetColorLevel(auto_level)
                print(f"{orientation} auto W/L: Window={auto_window:.1f}, Level={auto_level:.1f}")
            else:
                prop.SetColorWindow(2000)
                prop.SetColorLevel(400)
            
            prop.SetInterpolationTypeToLinear()
            
            self.renderer.AddViewProp(self.image_slice)
            
            self._add_crosshairs_to_renderer()
            self._setup_orientation_labels()
            
            camera = self.renderer.GetActiveCamera()
            camera.ParallelProjectionOn()
            self.renderer.ResetCamera()
            
            # === FIX: SYNC OVERLAY CAMERA FOR 2D VIEWS ===
            # This ensures the measurement layer matches the image layer's zoom/pan
            self.overlay_renderer.SetActiveCamera(camera)
            
            self._store_camera_state()
            
            self._setup_scroll_interaction()
            self._setup_click_interaction()
            self._enable_axes_widget()
            
            self._update_slice_text()
            
            if self.crosshair_manager:
                bounds = image_data.GetBounds()
                self.crosshair_manager.set_image_bounds(bounds)
                
                if self.crosshair_enabled:
                    x, y, z = self.crosshair_manager.current_center
                    self._update_crosshair_lines(x, y, z)
            
        except Exception as e:
            print(f"ERROR setting up {orientation} view: {e}")
            import traceback
            traceback.print_exc()

    def _update_slice_position(self, image_data=None):
        """Update the slice position for reslice filter."""
        if image_data is None:
            image_data = self.image_data_ref
        if image_data is None or self.reslice is None:
            return
            
        origin = image_data.GetOrigin()
        spacing = image_data.GetSpacing()
        
        if self.view_type == 'axial':
            pos = origin[2] + self.current_slice * spacing[2]
            self.reslice.SetResliceAxesOrigin(origin[0], origin[1], pos)
        elif self.view_type == 'sagittal':
            pos = origin[0] + self.current_slice * spacing[0]
            self.reslice.SetResliceAxesOrigin(pos, origin[1], origin[2])
        elif self.view_type == 'coronal':
            pos = origin[1] + self.current_slice * spacing[1]
            self.reslice.SetResliceAxesOrigin(origin[0], pos, origin[2])

    def _get_world_position_from_slice(self):
        """Get the current world position based on slice index."""
        if self.image_data_ref is None:
            return (0, 0, 0)
        
        origin = self.image_data_ref.GetOrigin()
        spacing = self.image_data_ref.GetSpacing()
        
        x, y, z = self.crosshair_manager.current_center if self.crosshair_manager else (origin[0], origin[1], origin[2])
        
        if self.view_type == 'axial':
            z = origin[2] + self.current_slice * spacing[2]
        elif self.view_type == 'sagittal':
            x = origin[0] + self.current_slice * spacing[0]
        elif self.view_type == 'coronal':
            y = origin[1] + self.current_slice * spacing[1]
        
        return (x, y, z)

    def _setup_scroll_interaction(self):
        """Setup mouse scroll for slice navigation with crosshair sync."""
        def on_scroll(obj, event):
            try:
                if event == "MouseWheelForwardEvent":
                    self.current_slice = min(self.current_slice + 1, self.max_slice)
                elif event == "MouseWheelBackwardEvent":
                    self.current_slice = max(self.current_slice - 1, 0)
                
                self._update_slice_position()
                if self.reslice:
                    self.reslice.Update()
                
                if self.crosshair_manager and self.crosshair_manager.enabled and self.crosshair_enabled:
                    x, y, z = self._get_world_position_from_slice()
                    
                    if self.view_type == 'axial':
                        self.crosshair_manager.set_position(z=z)
                    elif self.view_type == 'sagittal':
                        self.crosshair_manager.set_position(x=x)
                    elif self.view_type == 'coronal':
                        self.crosshair_manager.set_position(y=y)
                
                self._update_slice_text()
                
                self.vtk_widget.GetRenderWindow().Render()
                
            except Exception as e:
                print(f"Scroll error: {e}")
        
        interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        interactor.AddObserver("MouseWheelForwardEvent", on_scroll)
        interactor.AddObserver("MouseWheelBackwardEvent", on_scroll)

    def _setup_click_interaction(self):
        """Setup click AND drag interaction for crosshairs."""
        self.is_dragging = False

        def on_left_down(obj, event):
            # Only enable crosshair dragging if measurement tool is OFF
            if not self.measurement_enabled:
                self.is_dragging = True
                on_mouse_move(obj, event)

        def on_left_up(obj, event):
            self.is_dragging = False

        def on_mouse_move(obj, event):
            if not self.is_dragging:
                return
            
            if not self.crosshair_manager or not self.crosshair_manager.enabled or not self.crosshair_enabled:
                return
            
            try:
                interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
                click_pos = interactor.GetEventPosition()
                
                picker = vtk.vtkWorldPointPicker()
                picker.Pick(click_pos[0], click_pos[1], 0, self.renderer)
                world_pos = picker.GetPickPosition()
                
                if self.image_data_ref is None:
                    return
                
                bounds = self.image_data_ref.GetBounds()
                
                if self.view_type == 'axial':
                    new_x = max(bounds[0], min(bounds[1], world_pos[0]))
                    new_y = max(bounds[2], min(bounds[3], world_pos[1]))
                    self.crosshair_manager.set_position(x=new_x, y=new_y)
                    
                elif self.view_type == 'sagittal':
                    new_y = max(bounds[2], min(bounds[3], world_pos[1]))
                    new_z = max(bounds[4], min(bounds[5], world_pos[2]))
                    self.crosshair_manager.set_position(y=new_y, z=new_z)
                    
                elif self.view_type == 'coronal':
                    new_x = max(bounds[0], min(bounds[1], world_pos[0]))
                    new_z = max(bounds[4], min(bounds[5], world_pos[2]))
                    self.crosshair_manager.set_position(x=new_x, z=new_z)
                
            except Exception as e:
                print(f"Interaction error: {e}")
        
        interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        interactor.AddObserver("LeftButtonPressEvent", on_left_down)
        interactor.AddObserver("LeftButtonReleaseEvent", on_left_up)
        interactor.AddObserver("MouseMoveEvent", on_mouse_move)

    def setup_3d_view(self, image_data, volume_property):
        """Setup 3D volume rendering view."""
        if image_data is None:
            print("ERROR: No image data for 3D view")
            return
        
        try:
            self.image_data_ref = image_data
            dims = image_data.GetDimensions()
            print(f"Setting up 3D view with dims: {dims}")
            
            self.volume_mapper = vtk.vtkSmartVolumeMapper()
            self.volume_mapper.SetBlendModeToComposite()
            self.volume_mapper.SetRequestedRenderModeToGPU()
            self.volume_mapper.SetInputData(image_data)
            
            self.volume = vtk.vtkVolume()
            self.volume.SetMapper(self.volume_mapper)
            self.volume.SetProperty(volume_property)
            self.renderer.AddVolume(self.volume)  # Add to main renderer (Layer 0)

            # === ADD BOUNDING BOX ===
            self._setup_bounding_box(image_data)

            # Setup picker for measurements - Use VolumePicker for better surface picking
            try:
                picker = vtk.vtkVolumePicker()
                picker.SetTolerance(0.001)
                picker.PickFromListOn()
                picker.AddPickList(self.volume)
                self.vtk_widget.GetRenderWindow().GetInteractor().SetPicker(picker)
                self._volume_picker = picker
            except Exception as e:
                print(f"Could not setup volume picker: {e}")
            
            # === SETUP CLIPPING PLANE WIDGET ===
            self._setup_clipping_plane(image_data)
            
            # === SYNC CAMERAS BETWEEN LAYERS ===
            # Share camera between main and overlay renderer
            self.overlay_renderer.SetActiveCamera(self.renderer.GetActiveCamera())
            
            camera = self.renderer.GetActiveCamera()
            camera.ParallelProjectionOff()
            self.renderer.ResetCamera()
            
            self._store_camera_state()
            self._enable_axes_widget()
            
            if self.corner_annotation:
                self.corner_annotation.SetText(2, "3D VOLUME")
            
        except Exception as e:
            print(f"ERROR setting up 3D view: {e}")
            import traceback
            traceback.print_exc()

    def _setup_clipping_plane(self, image_data):
        """Setup the interactive clipping plane widget for 3D view."""
        if self.view_type != '3d' or image_data is None:
            return
        
        try:
            # Create the implicit plane for clipping
            self.clipping_plane = vtk.vtkPlane()
            
            # Get volume bounds and center
            bounds = image_data.GetBounds()
            center = [
                (bounds[0] + bounds[1]) / 2.0,
                (bounds[2] + bounds[3]) / 2.0,
                (bounds[4] + bounds[5]) / 2.0
            ]
            
            # Initialize plane at center with Z-normal (axial cut)
            self.clipping_plane.SetOrigin(center)
            self.clipping_plane.SetNormal(0, 0, 1)
            
            # Create the implicit plane representation
            plane_rep = vtk.vtkImplicitPlaneRepresentation()
            plane_rep.SetPlaceFactor(1.25)  # Slightly larger than volume
            plane_rep.PlaceWidget(bounds)
            plane_rep.SetOrigin(center)
            plane_rep.SetNormal(0, 0, 1)
            
            # Style the plane widget - make it more visible
            plane_rep.GetPlaneProperty().SetColor(0.0, 0.74, 0.83)  # Cyan (theme color)
            plane_rep.GetPlaneProperty().SetOpacity(0.3)
            plane_rep.GetPlaneProperty().SetLineWidth(2)
            
            plane_rep.GetSelectedPlaneProperty().SetColor(1.0, 1.0, 0.0)  # Yellow when selected
            plane_rep.GetSelectedPlaneProperty().SetOpacity(0.5)
            
            # Style the outline box
            plane_rep.GetOutlineProperty().SetColor(0.5, 0.5, 0.5)
            plane_rep.GetOutlineProperty().SetOpacity(0.3)
            
            # Style the normal arrow
            plane_rep.GetNormalProperty().SetColor(1.0, 0.5, 0.0)  # Orange
            plane_rep.GetNormalProperty().SetLineWidth(3)
            
            plane_rep.GetSelectedNormalProperty().SetColor(1.0, 1.0, 0.0)  # Yellow
            plane_rep.GetSelectedNormalProperty().SetLineWidth(4)
            
            # Style the edges
            plane_rep.GetEdgesProperty().SetColor(0.0, 0.74, 0.83)
            plane_rep.GetEdgesProperty().SetLineWidth(2)
            
            # Enable drawing of the plane outline
            plane_rep.SetDrawOutline(True)
            plane_rep.SetDrawPlane(True)
            
            # Create the widget
            self.clipping_plane_widget = vtk.vtkImplicitPlaneWidget2()
            self.clipping_plane_widget.SetInteractor(self.vtk_widget.GetRenderWindow().GetInteractor())
            self.clipping_plane_widget.SetRepresentation(plane_rep)
            self.clipping_plane_widget.SetDefaultRenderer(self.renderer)
            
            # Add observer to update clipping when plane moves
            def on_plane_interaction(obj, event):
                self._update_clipping_plane()
            
            self.clipping_plane_widget.AddObserver("InteractionEvent", on_plane_interaction)
            self.clipping_plane_widget.AddObserver("EndInteractionEvent", on_plane_interaction)
            
            # Initially disabled
            self.clipping_plane_widget.Off()
            self.clipping_enabled = False
            
            print("Clipping plane widget setup complete")
            
        except Exception as e:
            print(f"Error setting up clipping plane: {e}")
            import traceback
            traceback.print_exc()
            self.clipping_plane = None
            self.clipping_plane_widget = None

    def _update_clipping_plane(self):
        """Update the clipping plane based on widget position."""
        if self.clipping_plane_widget is None or self.volume_mapper is None:
            return
        
        try:
            # Get the plane parameters from the widget representation
            rep = self.clipping_plane_widget.GetRepresentation()
            origin = [0.0, 0.0, 0.0]
            normal = [0.0, 0.0, 0.0]
            rep.GetOrigin(origin)
            rep.GetNormal(normal)
            
            # Update the clipping plane
            self.clipping_plane.SetOrigin(origin)
            self.clipping_plane.SetNormal(normal)
            
            # Render to show changes
            self.render()
            
        except Exception as e:
            print(f"Error updating clipping plane: {e}")

    def set_clipping_enabled(self, enabled):
        """Enable or disable the clipping plane."""
        if self.view_type != '3d':
            return
        
        if self.clipping_plane_widget is None or self.volume_mapper is None:
            print("Clipping plane not initialized")
            return
        
        self.clipping_enabled = enabled
        
        try:
            if enabled:
                # Show the widget
                self.clipping_plane_widget.On()
                
                # Get current plane parameters from widget
                rep = self.clipping_plane_widget.GetRepresentation()
                origin = [0.0, 0.0, 0.0]
                normal = [0.0, 0.0, 0.0]
                rep.GetOrigin(origin)
                rep.GetNormal(normal)
                
                # Update the clipping plane
                self.clipping_plane.SetOrigin(origin)
                self.clipping_plane.SetNormal(normal)
                
                # Add clipping plane to mapper
                self.volume_mapper.AddClippingPlane(self.clipping_plane)
                
                print(f"Clipping enabled at origin {origin}, normal {normal}")
            else:
                # Hide the widget
                self.clipping_plane_widget.Off()
                
                # Remove all clipping planes from mapper
                self.volume_mapper.RemoveAllClippingPlanes()
                
                print("Clipping disabled")
            
            self.render()
            
        except Exception as e:
            print(f"Error toggling clipping: {e}")
            import traceback
            traceback.print_exc()

    def reset_clipping_plane(self):
        """Reset the clipping plane to its default position (center of volume, Z-normal)."""
        if self.view_type != '3d' or self.image_data_ref is None:
            return
        
        if self.clipping_plane_widget is None:
            return
        
        try:
            # Get volume bounds and center
            bounds = self.image_data_ref.GetBounds()
            center = [
                (bounds[0] + bounds[1]) / 2.0,
                (bounds[2] + bounds[3]) / 2.0,
                (bounds[4] + bounds[5]) / 2.0
            ]
            
            # Reset the widget representation
            rep = self.clipping_plane_widget.GetRepresentation()
            rep.SetOrigin(center)
            rep.SetNormal(0, 0, 1)
            
            # Update the clipping plane
            if self.clipping_enabled:
                self._update_clipping_plane()
            
            self.render()
            print("Clipping plane reset to default position")
            
        except Exception as e:
            print(f"Error resetting clipping plane: {e}")

    def set_clipping_plane_orientation(self, orientation):
        """Set the clipping plane to a preset orientation (axial, sagittal, coronal)."""
        if self.view_type != '3d' or self.image_data_ref is None:
            return
        
        if self.clipping_plane_widget is None:
            return
        
        try:
            # Get volume bounds and center
            bounds = self.image_data_ref.GetBounds()
            center = [
                (bounds[0] + bounds[1]) / 2.0,
                (bounds[2] + bounds[3]) / 2.0,
                (bounds[4] + bounds[5]) / 2.0
            ]
            
            # Set normal based on orientation
            if orientation == 'axial':
                normal = [0, 0, 1]  # Z-normal
            elif orientation == 'sagittal':
                normal = [1, 0, 0]  # X-normal
            elif orientation == 'coronal':
                normal = [0, 1, 0]  # Y-normal
            else:
                normal = [0, 0, 1]  # Default to axial
            
            # Update the widget representation
            rep = self.clipping_plane_widget.GetRepresentation()
            rep.SetOrigin(center)
            rep.SetNormal(normal)
            
            # Update the clipping plane if enabled
            if self.clipping_enabled:
                self._update_clipping_plane()
            
            self.render()
            print(f"Clipping plane set to {orientation} orientation")
            
        except Exception as e:
            print(f"Error setting clipping plane orientation: {e}")

    def _setup_bounding_box(self, image_data):
        """Setup a bounding box outline around the volume with theme color and dimension labels."""
        if image_data is None:
            return
        
        try:
            # Get the bounds of the image data
            bounds = image_data.GetBounds()
            
            # Create an outline filter using vtkOutlineFilter
            outline = vtk.vtkOutlineFilter()
            outline.SetInputData(image_data)
            outline.Update()
            
            # Create mapper for the outline
            outline_mapper = vtk.vtkPolyDataMapper()
            outline_mapper.SetInputConnection(outline.GetOutputPort())
            
            # Create actor for the outline
            self.bounding_box_actor = vtk.vtkActor()
            self.bounding_box_actor.SetMapper(outline_mapper)
            
            # Set the color to match theme (#00bcd4 = RGB 0, 188, 212)
            # Normalized to 0-1 range: (0/255, 188/255, 212/255)
            self.bounding_box_actor.GetProperty().SetColor(0.0, 0.737, 0.831)
            self.bounding_box_actor.GetProperty().SetLineWidth(2.0)
            self.bounding_box_actor.GetProperty().SetOpacity(0.8)
            
            # Add to renderer
            self.renderer.AddActor(self.bounding_box_actor)
            
            # Store reference for later control
            self.bounding_box_visible = True
            
            # === ADD DIMENSION LABELS ===
            self._setup_bounding_box_labels(bounds)
            
            print(f"Bounding box created with bounds: {bounds}")
            
        except Exception as e:
            print(f"Error creating bounding box: {e}")
            self.bounding_box_actor = None

    def _setup_bounding_box_labels(self, bounds):
        """Setup dimension labels for the bounding box using vtkFollower."""
        try:
            # Get the actual physical dimensions from the image data
            # bounds already accounts for spacing, so we use them directly
            # BUT we need to verify the spacing is being applied correctly
            
            if self.image_data_ref:
                spacing = self.image_data_ref.GetSpacing()
                dims = self.image_data_ref.GetDimensions()
                
                # Calculate TRUE physical dimensions using spacing
                # Physical size = (number of pixels - 1) * spacing
                x_dim = (dims[0] - 1) * spacing[0]  # Width (X) in mm
                y_dim = (dims[1] - 1) * spacing[1]  # Depth (Y) in mm
                z_dim = (dims[2] - 1) * spacing[2]  # Height (Z) in mm
                
                print(f"Image dims: {dims}, spacing: {spacing}")
                print(f"Physical dimensions: X={x_dim:.1f}mm, Y={y_dim:.1f}mm, Z={z_dim:.1f}mm")
            else:
                # Fallback to bounds-based calculation
                x_dim = bounds[1] - bounds[0]
                y_dim = bounds[3] - bounds[2]
                z_dim = bounds[5] - bounds[4]
            
            # Calculate center of the volume
            center_x = (bounds[0] + bounds[1]) / 2.0
            center_y = (bounds[2] + bounds[3]) / 2.0
            center_z = (bounds[4] + bounds[5]) / 2.0
            
            # Offset for label positioning (slightly outside the box)
            max_dim = max(x_dim, y_dim, z_dim)
            offset = max_dim * 0.05
            
            # Store label actors for later control
            self.bbox_label_actors = []
            
            # === X DIMENSION LABEL (Width) ===
            # Position at the center of the bottom X edge
            x_label_pos = [center_x, bounds[2] - offset, bounds[4] - offset]
            x_label = self._create_dimension_label(f"{x_dim:.1f}", x_label_pos)
            self.bbox_label_actors.append(x_label)
            
            # === Y DIMENSION LABEL (Depth) ===
            # Position at the center of the left Y edge
            y_label_pos = [bounds[0] - offset, center_y, bounds[4] - offset]
            y_label = self._create_dimension_label(f"{y_dim:.1f}", y_label_pos)
            self.bbox_label_actors.append(y_label)
            
            # === Z DIMENSION LABEL (Height) ===
            # Position at the center of the left Z edge
            z_label_pos = [bounds[0] - offset, bounds[2] - offset, center_z]
            z_label = self._create_dimension_label(f"{z_dim:.1f}", z_label_pos)
            self.bbox_label_actors.append(z_label)
            
            # Add all labels to renderer
            for label_actor in self.bbox_label_actors:
                self.renderer.AddActor(label_actor)
            
            # Labels visible by default
            self.bbox_labels_visible = True
            
            print(f"Bounding box dimensions: X={x_dim:.1f}mm, Y={y_dim:.1f}mm, Z={z_dim:.1f}mm")
            
        except Exception as e:
            print(f"Error creating bounding box labels: {e}")
            import traceback
            traceback.print_exc()
            self.bbox_label_actors = []
            
    def _create_dimension_label(self, text, position):
        """Create a vtkFollower text label that always faces the camera."""
        # Create vector text
        vector_text = vtk.vtkVectorText()
        vector_text.SetText(text)
        vector_text.Update()
        
        # Create mapper
        text_mapper = vtk.vtkPolyDataMapper()
        text_mapper.SetInputConnection(vector_text.GetOutputPort())
        
        # Create follower (billboard text that always faces camera)
        follower = vtk.vtkFollower()
        follower.SetMapper(text_mapper)
        follower.SetPosition(position)
        
        # Scale the text appropriately based on scene size
        # Get the bounds of the text to calculate scale
        text_bounds = vector_text.GetOutput().GetBounds()
        text_width = text_bounds[1] - text_bounds[0]
        
        # Calculate scale factor - aim for labels about 5% of the largest dimension
        if hasattr(self, 'image_data_ref') and self.image_data_ref:
            img_bounds = self.image_data_ref.GetBounds()
            max_dim = max(img_bounds[1] - img_bounds[0], 
                         img_bounds[3] - img_bounds[2], 
                         img_bounds[5] - img_bounds[4])
            target_size = max_dim * 0.08
            if text_width > 0:
                scale = target_size / text_width
            else:
                scale = 5.0
        else:
            scale = 5.0
        
        follower.SetScale(scale, scale, scale)
        
        # Set color - white with slight yellow tint for visibility
        follower.GetProperty().SetColor(1.0, 1.0, 0.8)
        follower.GetProperty().SetOpacity(1.0)
        
        # Set the camera for the follower to track
        follower.SetCamera(self.renderer.GetActiveCamera())
        
        return follower
    
    def set_bbox_labels_visible(self, visible):
        """Toggle bounding box dimension labels visibility."""
        if hasattr(self, 'bbox_label_actors') and self.bbox_label_actors:
            for actor in self.bbox_label_actors:
                actor.SetVisibility(visible)
            self.bbox_labels_visible = visible
            self.render()

    def set_bounding_box_visible(self, visible):
        """Toggle bounding box visibility."""
        if hasattr(self, 'bounding_box_actor') and self.bounding_box_actor:
            self.bounding_box_actor.SetVisibility(visible)
            self.bounding_box_visible = visible
            self.render()

    def set_bounding_box_color(self, r, g, b):
        """Set bounding box color (values 0-1)."""
        if hasattr(self, 'bounding_box_actor') and self.bounding_box_actor:
            self.bounding_box_actor.GetProperty().SetColor(r, g, b)
            self.render()

    def set_bounding_box_line_width(self, width):
        """Set bounding box line width."""
        if hasattr(self, 'bounding_box_actor') and self.bounding_box_actor:
            self.bounding_box_actor.GetProperty().SetLineWidth(width)
            self.render()

    def _store_camera_state(self):
        """Store initial camera state for reset."""
        try:
            camera = self.renderer.GetActiveCamera()
            self.initial_camera_state = {
                'position': camera.GetPosition(),
                'focal_point': camera.GetFocalPoint(),
                'view_up': camera.GetViewUp(),
                'parallel_scale': camera.GetParallelScale()
            }
        except Exception as e:
            print(f"Warning: Could not store camera state: {e}")

    def reset_camera(self):
        """Reset camera to initial state."""
        try:
            if self.initial_camera_state:
                camera = self.renderer.GetActiveCamera()
                camera.SetPosition(self.initial_camera_state['position'])
                camera.SetFocalPoint(self.initial_camera_state['focal_point'])
                camera.SetViewUp(self.initial_camera_state['view_up'])
                if self.view_type != '3d':
                    camera.SetParallelScale(self.initial_camera_state['parallel_scale'])
                self.renderer.ResetCameraClippingRange()
                self._update_slice_text()
                self.render()
        except Exception as e:
            print(f"Warning: Could not reset camera: {e}")

    def clear(self):
        """Clear all actors from renderer."""
        try:
            # Disable clipping before clearing
            if self.clipping_plane_widget:
                self.clipping_plane_widget.Off()
            if self.volume_mapper:
                self.volume_mapper.RemoveAllClippingPlanes()
            
            self.renderer.RemoveAllViewProps()
            self.overlay_renderer.RemoveAllViewProps()  # Clear overlay renderer too
            
            if self.corner_annotation:
                self.renderer.AddViewProp(self.corner_annotation)
                self.corner_annotation.SetText(0, "")
                self.corner_annotation.SetText(1, "")
                self.corner_annotation.SetText(2, f"{self.label_text}")
                self.corner_annotation.SetText(3, "")
            
            self.image_slice = None
            self.slice_mapper = None
            self.reslice = None
            self.volume = None
            self.volume_mapper = None
            self.image_data_ref = None
            self.orientation_actors = {}
            
            # Clear bounding box reference
            self.bounding_box_actor = None
            
            # Clear bounding box labels
            self.bbox_label_actors = []
            self.bbox_labels_visible = True
            
            # Clear scale ruler reference (will be re-added in setup_3d_view)
            self.legend_scale_actor = None
            
            # Clear clipping plane
            self.clipping_plane = None
            self.clipping_plane_widget = None
            self.clipping_enabled = False
            
            self._setup_crosshairs()
            
            # Re-setup scale rulers for 3D view after clear
            if self.view_type == '3d':
                self._setup_scale_rulers()
            
            # Clear all measurements
            for widget in self.distance_widgets:
                widget.Off()
                widget.SetInteractor(None)
            self.distance_widgets.clear()
            
            if self.active_distance_widget:
                self.active_distance_widget.Off()
                self.active_distance_widget.SetInteractor(None)
                self.active_distance_widget = None
            
        except Exception as e:
            print(f"Warning: Error clearing viewport: {e}")

    def render(self):
        """Render the viewport."""
        try:
            # === FIX: SYNC CAMERAS FOR ALL VIEWS (2D AND 3D) ===
            # Previously this was only for 3D. Now we ensure 2D views also sync.
            # This fixes the "0.00 mm" measurement bug caused by scale mismatch.
            if hasattr(self, 'overlay_renderer'):
                self.overlay_renderer.SetActiveCamera(self.renderer.GetActiveCamera())
            
            self.vtk_widget.GetRenderWindow().Render()
        except Exception as e:
            print(f"Warning: Render error: {e}")

    def initialize(self):
        """Initialize the interactor."""
        try:
            self.vtk_widget.GetRenderWindow().GetInteractor().Initialize()
        except Exception as e:
            print(f"Warning: Initialize error: {e}")

    def finalize(self):
        """Finalize/cleanup the VTK widget."""
        try:
            if self.axes_widget:
                self.axes_widget.SetEnabled(0)
            
            # Clean up clipping widget
            if self.clipping_plane_widget:
                self.clipping_plane_widget.Off()
            
            # Clean up distance widgets
            for widget in self.distance_widgets:
                widget.Off()
            if self.active_distance_widget:
                self.active_distance_widget.Off()
            
            self.vtk_widget.Finalize()
        except Exception as e:
            print(f"Warning: Finalize error: {e}")


# ============================================================================
# MAIN WINDOW
# ============================================================================

class MainWindow(QMainWindow):
    """Main Window with Study Browser and Medical DICOM Viewer Layout."""
    
    def __init__(self, parent=None, auto_show=True):
        super().__init__(parent)
        self.setWindowTitle("Medical DICOM Visualizer")
        self.setGeometry(50, 50, 1800, 1000)
        self.setStyleSheet(DARK_STYLE)
        
        self.vtk_handler = myVTK()
        self.current_dicom_path = None
        self.current_series_info = None
        self.current_preset = 'bone'  # Add this line
        self.viewports = {}
        
        # Create crosshair manager
        self.crosshair_manager = CrosshairManager()
        
        self.setup_ui()
        self.create_menus()
        self.create_custom_toolbar()
        self.setup_study_browser()
        
        if auto_show:
            self.show()
    
    def setup_ui(self):
        """Setup the main UI layout - 2D views on left, 3D on right, controls at bottom."""
        central_widget = QWidget()
        central_widget.setObjectName("CentralArea")
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # ============ TOP AREA: Viewports ============
        viewport_splitter = QSplitter(Qt.Horizontal)
        viewport_splitter.setHandleWidth(3)
        viewport_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3d3d3d;
            }
            QSplitter::handle:hover {
                background-color: #00bcd4;
            }
        """)
        
        # LEFT SIDE: 2D Views (stacked vertically with scroll)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        
        # Create scroll area for 2D views
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #000000;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00bcd4;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container for 2D viewports
        views_container = QWidget()
        views_layout = QVBoxLayout(views_container)
        views_layout.setContentsMargins(2, 2, 2, 2)
        views_layout.setSpacing(5)
        
        # Create 2D viewports with frames
        view_configs = [
            ('axial', 'AXIAL'),
            ('sagittal', 'SAGITTAL'),
            ('coronal', 'CORONAL')
        ]
        
        for view_type, label in view_configs:
            # Frame for each viewport
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    background-color: #000000;
                    border: 1px solid #2a2a2a;
                    border-radius: 4px;
                }
            """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(2, 2, 2, 2)
            frame_layout.setSpacing(0)
            
            # Create viewport
            self.viewports[view_type] = ViewportWidget(frame, view_type, label, self.crosshair_manager)
            self.viewports[view_type].vtk_widget.setMinimumSize(280, 220)
            self.viewports[view_type].vtk_widget.setMaximumHeight(300)
            frame_layout.addWidget(self.viewports[view_type].vtk_widget)
            
            # Slice slider for each 2D view
            slider_container = QWidget()
            slider_container.setFixedHeight(25)
            slider_layout = QHBoxLayout(slider_container)
            slider_layout.setContentsMargins(5, 2, 5, 2)
            slider_layout.setSpacing(5)
            
            slice_label = QLabel("0")
            slice_label.setFixedWidth(30)
            slice_label.setStyleSheet("color: #00bcd4; font-size: 10px;")
            slice_label.setAlignment(Qt.AlignCenter)
            
            slice_slider = QSlider(Qt.Horizontal)
            slice_slider.setRange(0, 100)
            slice_slider.setValue(50)
            slice_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 4px;
                    background: #2a2a2a;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #00bcd4;
                    width: 12px;
                    height: 12px;
                    margin: -4px 0;
                    border-radius: 6px;
                }
                QSlider::handle:horizontal:hover {
                    background: #00e5ff;
                }
            """)
            
            # Store references
            setattr(self, f'{view_type}_slider', slice_slider)
            setattr(self, f'{view_type}_slice_label', slice_label)
            
            # Connect slider
            slice_slider.valueChanged.connect(
                lambda v, vt=view_type, lbl=slice_label: self._on_slice_slider_changed(vt, v, lbl)
            )
            
            slider_layout.addWidget(slice_label)
            slider_layout.addWidget(slice_slider)
            
            frame_layout.addWidget(slider_container)
            views_layout.addWidget(frame)
        
        views_layout.addStretch()
        scroll_area.setWidget(views_container)
        left_layout.addWidget(scroll_area)
        
        # RIGHT SIDE: 3D View (larger)
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(0)
        
        # 3D Viewport
        self.viewports['3d'] = ViewportWidget(right_panel, '3d', '3D VOLUME', self.crosshair_manager)
        self.viewports['3d'].vtk_widget.setMinimumSize(500, 400)
        right_layout.addWidget(self.viewports['3d'].vtk_widget)
        
        # Connect the floating rotation buttons
        self.viewports['3d'].connect_rotation_buttons(self.rotate_3d_view)
        
        # Add panels to splitter
        viewport_splitter.addWidget(left_panel)
        viewport_splitter.addWidget(right_panel)
        
        # Set initial sizes (left: 420px, right: rest)
        viewport_splitter.setSizes([420, 1000])
        viewport_splitter.setStretchFactor(0, 0)  # Left doesn't stretch
        viewport_splitter.setStretchFactor(1, 1)  # Right stretches
        
        main_layout.addWidget(viewport_splitter, stretch=4)
        
        # ============ BOTTOM AREA: Dashboard Panels ============
        dashboard = QWidget()
        dashboard.setFixedHeight(220)
        dashboard_layout = QHBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(5, 10, 5, 10)
        dashboard_layout.setSpacing(10)
        
        self.create_panel_data_view(dashboard_layout)
        self.create_panel_adjustments(dashboard_layout)
        self.create_panel_color_presets(dashboard_layout)  # NEW: Color presets panel
        self.create_panel_presets(dashboard_layout)  # Added new panel
        self.create_panel_tools(dashboard_layout)
        
        main_layout.addWidget(dashboard)
        
        # Initialize all viewports
        for viewport in self.viewports.values():
            viewport.initialize()

    def _on_slice_slider_changed(self, view_type, value, label):
        """Handle slice slider change for a specific view."""
        if view_type not in self.viewports:
            return
        
        viewport = self.viewports[view_type]
        if viewport.max_slice <= 0:
            return
        
        # Calculate slice index from slider value (0-100 -> 0-max_slice)
        slice_idx = int((value / 100.0) * viewport.max_slice)
        slice_idx = max(0, min(slice_idx, viewport.max_slice))
        
        viewport.current_slice = slice_idx
        viewport._update_slice_position()
        if viewport.reslice:
            viewport.reslice.Update()
        viewport._update_slice_text()
        viewport.render()
        
        # Update label
        label.setText(str(slice_idx))
        
        # Update crosshairs if enabled
        if self.crosshair_manager and self.crosshair_manager.enabled and viewport.crosshair_enabled:
            x, y, z = viewport._get_world_position_from_slice()
            if view_type == 'axial':
                self.crosshair_manager.set_position(z=z)
            elif view_type == 'sagittal':
                self.crosshair_manager.set_position(x=x)
            elif view_type == 'coronal':
                self.crosshair_manager.set_position(y=y)

    def _update_slice_sliders(self):
        """Update slice sliders when new data is loaded."""
        for view_type in ['axial', 'sagittal', 'coronal']:
            if view_type in self.viewports:
                viewport = self.viewports[view_type]
                slider = getattr(self, f'{view_type}_slider', None)
                label = getattr(self, f'{view_type}_slice_label', None)
                
                if slider and viewport.max_slice > 0:
                    # Set slider to middle
                    slider.blockSignals(True)
                    slider.setValue(50)
                    slider.blockSignals(False)
                    
                    if label:
                        label.setText(str(viewport.current_slice))

    def setup_study_browser(self):
        """Setup the study browser sidebar."""
        self.study_browser = StudyBrowser()
        self.study_browser.series_selected.connect(self._on_series_selected)
        
        dock = QDockWidget("Study Browser", self)  # Shorter title
        dock.setWidget(self.study_browser)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock.setMinimumWidth(220)
        dock.setMaximumWidth(350)
        
        # Style the dock widget title bar
        dock.setStyleSheet("""
            QDockWidget {
                color: #e0e0e0;
                font-size: 11px;
            }
            QDockWidget::title {
                background-color: #1e1e1e;
                padding: 6px 8px;
                border-bottom: 1px solid #00bcd4;
                text-align: left;
            }
        """)
        
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    
    def create_panel_data_view(self, parent_layout):
        """Create the Data & View panel."""
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)  # Increased padding
        layout.setSpacing(8)  # Increased spacing
        
        header = QLabel("DATA & VIEW")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)
        
        layout.addSpacing(5)
        
        # Dataset selector
        ds_layout = QHBoxLayout()
        ds_layout.addWidget(QLabel("Active Series:"))
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(["No Data Loaded"])
        self.dataset_combo.setMinimumWidth(100)
        ds_layout.addWidget(self.dataset_combo, stretch=1)
        layout.addLayout(ds_layout)
        
        # Series info display
        self.series_info_label = QLabel("Modality: --\nImages: --\nDimensions: --")
        self.series_info_label.setStyleSheet("color: #808080; font-size: 11px;")
        self.series_info_label.setWordWrap(True)
        layout.addWidget(self.series_info_label)
        
        layout.addStretch()
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #3d3d3d;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        layout.addSpacing(5)
        
        btn_bg = QPushButton("Change Background")
        btn_bg.clicked.connect(self.change_background)
        layout.addWidget(btn_bg)
        
        parent_layout.addWidget(panel)

    def create_panel_presets(self, parent_layout):
        """Create a separate panel for Tissue Presets."""
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setMinimumWidth(200)
        panel.setMaximumWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        header = QLabel("TISSUE PRESETS")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)
        
        layout.addSpacing(5)
        
        # Grid layout for presets
        grid = QGridLayout()
        grid.setSpacing(8)
        
        # Store preset buttons for later style updates
        self.preset_buttons = {}
        
        presets = [
            ("Bone", 'bone', 0, 0),
            ("Soft Tissue", 'soft', 0, 1),
            ("Muscle", 'muscle', 1, 0),
            ("Auto", 'auto', 1, 1),
            ("X-Ray", 'xray', 2, 0),
            ("MRI", 'mri', 2, 1)
        ]
        
        # Default (unselected) button style
        self.preset_btn_default_style = """
            QPushButton {
                font-size: 11px; 
                padding: 8px;
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #00bcd4;
                color: black;
            }
        """
        
        # Selected button style
        self.preset_btn_selected_style = """
            QPushButton {
                font-size: 11px; 
                padding: 8px;
                background-color: #00bcd4;
                color: black;
                border: 1px solid #00bcd4;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00e5ff;
                color: black;
            }
        """
        
        for name, key, r, c in presets:
            btn = QPushButton(name)
            btn.setStyleSheet(self.preset_btn_default_style)
            btn.clicked.connect(lambda checked, p=key: self.apply_tissue_preset(p))
            grid.addWidget(btn, r, c)
            self.preset_buttons[key] = btn
            
        layout.addLayout(grid)
        layout.addStretch()
        
        parent_layout.addWidget(panel)
    
    def create_panel_adjustments(self, parent_layout):
        """Create the Adjustments panel (Sliders only)."""
        # Initialize the dictionary to store slider references
        self.adjustment_sliders = {}
        
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        # Allow this panel to expand horizontally
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        header = QLabel("ADJUSTMENTS")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)
        
        layout.addSpacing(3)
        
        # All sliders in a single column
        sliders_layout = QVBoxLayout()
        sliders_layout.setSpacing(5)
        
        # All slider data - expanded with new controls
        # Format: (label, key, default, min, max, is_float)
        slider_data = [
            ("Ambient:", "ambient", 40, 0, 100, False),
            ("Diffuse:", "diffuse", 60, 0, 100, False),
            ("Specular:", "specular", 20, 0, 100, False),
            ("Spec Power:", "specular_power", 10, 1, 128, False),
            ("Opacity:", "global_opacity", 100, 0, 100, False),
            ("Win Width:", "window_width", 50, 0, 100, False),
            ("Win Level:", "window_level", 50, 0, 100, False),
        ]
        
        for label_text, key, default_val, min_val, max_val, is_float in slider_data:
            row = QHBoxLayout()
            row.setSpacing(6)
            
            lbl = QLabel(label_text)
            lbl.setFixedWidth(70)
            lbl.setStyleSheet("font-size: 10px;")
            row.addWidget(lbl)
            
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default_val)
            slider.valueChanged.connect(lambda v, k=key: self.on_adjustment_changed(k, v))
            self.adjustment_sliders[key] = slider
            row.addWidget(slider)
            
            # Value label with appropriate formatting
            if key == "specular_power":
                val_lbl = QLabel(str(default_val))
            else:
                val_lbl = QLabel(str(default_val))
            val_lbl.setFixedWidth(28)
            val_lbl.setStyleSheet("color: #00bcd4; font-size: 10px;")
            val_lbl.setAlignment(Qt.AlignCenter)
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(str(v)))
            row.addWidget(val_lbl)
            
            sliders_layout.addLayout(row)
        
        layout.addLayout(sliders_layout)
        layout.addStretch()
        
        parent_layout.addWidget(panel, stretch=1)

    def create_panel_color_presets(self, parent_layout):
        """Create a panel for Color Map Presets."""
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setMinimumWidth(200)
        panel.setMaximumWidth(260)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        header = QLabel("COLOR PRESETS")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)
        
        layout.addSpacing(5)
        
        # Grid layout for color presets
        grid = QGridLayout()
        grid.setSpacing(8)
        
        # Store color preset buttons for later style updates
        self.color_buttons = {}
        
        color_presets = [
            ("Grayscale", 'gray', 0, 0),
            ("Inverse", 'inverse', 0, 1),
            ("CT Hot", 'hot', 1, 0),
            ("Rainbow", 'rainbow', 1, 1)
        ]
        
        # Default (unselected) button style
        self.color_btn_default_style = """
            QPushButton {
                font-size: 11px; 
                padding: 8px;
                min-height: 35px;
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #00bcd4;
                color: black;
            }
        """
        
        # Selected button style
        self.color_btn_selected_style = """
            QPushButton {
                font-size: 11px; 
                padding: 8px;
                min-height: 35px;
                background-color: #00bcd4;
                color: black;
                border: 1px solid #00bcd4;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00e5ff;
                color: black;
            }
        """
        
        for name, key, r, c in color_presets:
            btn = QPushButton(name)
            btn.setStyleSheet(self.color_btn_default_style)
            btn.setFixedHeight(35)
            btn.clicked.connect(lambda checked, p=key: self.apply_colormap(p))
            grid.addWidget(btn, r, c)
            self.color_buttons[key] = btn
        
        # Set grayscale as initially selected
        self.current_colormap = 'gray'
        self.color_buttons['gray'].setStyleSheet(self.color_btn_selected_style)
            
        layout.addLayout(grid)
        layout.addStretch()
        
        parent_layout.addWidget(panel)

    def _update_color_button_styles(self, selected_colormap):
        """Update color preset button styles to show which one is selected."""
        if not hasattr(self, 'color_buttons'):
            return
        
        for key, btn in self.color_buttons.items():
            if key == selected_colormap:
                btn.setStyleSheet(self.color_btn_selected_style)
            else:
                btn.setStyleSheet(self.color_btn_default_style)

    def apply_colormap(self, mode):
        """Apply color map preset to all viewports."""
        if not self.vtk_handler.is_loaded:
            QMessageBox.warning(self, "Warning", "Please load DICOM data first.")
            return
        
        try:
            self.current_colormap = mode
            self._update_color_button_styles(mode)
            
            # Apply to 2D views
            for view_type in ['axial', 'sagittal', 'coronal']:
                if view_type in self.viewports:
                    vp = self.viewports[view_type]
                    if vp.image_slice:
                        self._apply_2d_colormap(vp, mode)
            
            # Apply to 3D view
            if '3d' in self.viewports and self.viewports['3d'].volume:
                self._apply_3d_colormap(mode)
            
            # Render all viewports
            for vp in self.viewports.values():
                vp.render()
            
            mode_names = {
                'gray': 'Grayscale',
                'inverse': 'Inverse',
                'hot': 'CT Hot',
                'rainbow': 'Rainbow'
            }
            self.statusBar().showMessage(f"Applied color map: {mode_names.get(mode, mode)}", 2000)
            
        except Exception as e:
            print(f"Colormap error: {e}")
            import traceback
            traceback.print_exc()

    def _apply_2d_colormap(self, viewport, mode):
        """Apply color lookup table to a 2D viewport."""
        if viewport.image_slice is None:
            return
        
        prop = viewport.image_slice.GetProperty()
        
        # Get current window/level
        window = prop.GetColorWindow()
        level = prop.GetColorLevel()
        
        # Calculate min/max from window/level
        min_val = level - window / 2.0
        max_val = level + window / 2.0
        
        # Create lookup table
        lut = vtk.vtkWindowLevelLookupTable()
        lut.SetNumberOfTableValues(256)
        
        if mode == 'gray':
            # Standard grayscale
            lut.SetHueRange(0.0, 0.0)
            lut.SetSaturationRange(0.0, 0.0)
            lut.SetValueRange(0.0, 1.0)
            lut.SetTableRange(min_val, max_val)
            
        elif mode == 'inverse':
            # Inverted grayscale (white to black)
            lut.SetHueRange(0.0, 0.0)
            lut.SetSaturationRange(0.0, 0.0)
            lut.SetValueRange(1.0, 0.0)  # Inverted
            lut.SetTableRange(min_val, max_val)
            
        elif mode == 'hot':
            # CT Hot: Black -> Red -> Yellow -> White
            lut.SetTableRange(min_val, max_val)
            lut.Build()
            # Manually set hot colormap
            for i in range(256):
                t = i / 255.0
                if t < 0.33:
                    # Black to Red
                    r = t / 0.33
                    g = 0.0
                    b = 0.0
                elif t < 0.66:
                    # Red to Yellow
                    r = 1.0
                    g = (t - 0.33) / 0.33
                    b = 0.0
                else:
                    # Yellow to White
                    r = 1.0
                    g = 1.0
                    b = (t - 0.66) / 0.34
                lut.SetTableValue(i, r, g, b, 1.0)
                
        elif mode == 'rainbow':
            # Rainbow spectrum
            lut.SetHueRange(0.667, 0.0)  # Blue to Red (rainbow)
            lut.SetSaturationRange(1.0, 1.0)
            lut.SetValueRange(1.0, 1.0)
            lut.SetTableRange(min_val, max_val)
        
        lut.Build()
        
        # Apply lookup table to image property
        prop.SetLookupTable(lut)
        prop.UseLookupTableScalarRangeOn()

    def _apply_3d_colormap(self, mode):
        """Apply color transfer function to 3D volume."""
        if self.vtk_handler.imageData is None:
            return
        
        color = self.vtk_handler.color
        scalar_range = self.vtk_handler.imageData.GetScalarRange()
        min_val, max_val = scalar_range
        data_range = max_val - min_val
        
        color.RemoveAllPoints()
        
        if mode == 'gray':
            # Grayscale
            color.AddRGBPoint(min_val, 0.0, 0.0, 0.0)
            color.AddRGBPoint(max_val, 1.0, 1.0, 1.0)
            
        elif mode == 'inverse':
            # Inverted grayscale
            color.AddRGBPoint(min_val, 1.0, 1.0, 1.0)
            color.AddRGBPoint(max_val, 0.0, 0.0, 0.0)
            
        elif mode == 'hot':
            # CT Hot: Black -> Red -> Yellow -> White
            color.AddRGBPoint(min_val, 0.0, 0.0, 0.0)                    # Black
            color.AddRGBPoint(min_val + data_range * 0.33, 1.0, 0.0, 0.0)  # Red
            color.AddRGBPoint(min_val + data_range * 0.66, 1.0, 1.0, 0.0)  # Yellow
            color.AddRGBPoint(max_val, 1.0, 1.0, 1.0)                    # White
            
        elif mode == 'rainbow':
            # Rainbow: Blue -> Cyan -> Green -> Yellow -> Red
            color.AddRGBPoint(min_val, 0.0, 0.0, 1.0)                    # Blue
            color.AddRGBPoint(min_val + data_range * 0.25, 0.0, 1.0, 1.0)  # Cyan
            color.AddRGBPoint(min_val + data_range * 0.50, 0.0, 1.0, 0.0)  # Green
            color.AddRGBPoint(min_val + data_range * 0.75, 1.0, 1.0, 0.0)  # Yellow
            color.AddRGBPoint(max_val, 1.0, 0.0, 0.0)                    # Red
        
        self.vtk_handler.volumeProperty.SetColor(color)

    def _update_preset_button_styles(self, selected_preset):
        """Update preset button styles to show which one is selected."""
        if not hasattr(self, 'preset_buttons'):
            return
        
        for key, btn in self.preset_buttons.items():
            if key == selected_preset:
                btn.setStyleSheet(self.preset_btn_selected_style)
            else:
                btn.setStyleSheet(self.preset_btn_default_style)

    def create_panel_tools(self, parent_layout):
        """Create the Tools panel with measurement and crosshair controls."""
        panel = QFrame()
        panel.setObjectName("DashboardPanel")
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(400)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        
        header = QLabel("TOOLS")
        header.setObjectName("HeaderLabel")
        layout.addWidget(header)
        
        layout.addSpacing(5)
        
        # Three-column layout for tools
        tools_row = QHBoxLayout()
        tools_row.setSpacing(15)
        
        # LEFT COLUMN: Measurement
        measure_col = QVBoxLayout()
        measure_col.setSpacing(5)
        
        measure_header = QLabel("Measurement Tool:")
        measure_header.setStyleSheet("color: #00bcd4; font-weight: bold; font-size: 11px;")
        measure_col.addWidget(measure_header)
        
        self.ruler_checkbox = QCheckBox("Enable Ruler Mode")
        self.ruler_checkbox.setStyleSheet("""
            QCheckBox { color: #e0e0e0; font-size: 11px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { background-color: #2a2a2a; border: 1px solid #3d3d3d; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #ffff00; border: 1px solid #ffff00; border-radius: 3px; }
        """)
        self.ruler_checkbox.toggled.connect(self._on_ruler_toggle)
        measure_col.addWidget(self.ruler_checkbox)
        
        # Unit selector row
        unit_row = QHBoxLayout()
        unit_row.setSpacing(5)
        
        unit_label = QLabel("Unit:")
        unit_label.setStyleSheet("color: #808080; font-size: 10px;")
        unit_label.setFixedWidth(30)
        unit_row.addWidget(unit_label)
        
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["mm", "px"])
        self.unit_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                padding: 3px 8px;
                font-size: 10px;
                border-radius: 3px;
            }
            QComboBox:hover {
                border: 1px solid #00bcd4;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #00bcd4;
                font-size: 10px;
            }
        """)
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        unit_row.addWidget(self.unit_combo)
        unit_row.addStretch()
        
        measure_col.addLayout(unit_row)
        
        self.measurement_count_label = QLabel("Measurements: 0")
        self.measurement_count_label.setStyleSheet("color: #00bcd4; font-size: 10px;")
        measure_col.addWidget(self.measurement_count_label)
        
        measure_btn_row = QHBoxLayout()
        measure_btn_row.setSpacing(3)
        
        btn_clear_last = QPushButton("Undo")
        btn_clear_last.setStyleSheet("""
            QPushButton { background-color: #3d3d3d; color: #ffaa00; padding: 4px 8px; font-size: 9px; }
            QPushButton:hover { background-color: #ffaa00; color: black; }
        """)
        btn_clear_last.clicked.connect(self._clear_last_measurement)
        measure_btn_row.addWidget(btn_clear_last)
        
        btn_clear_all = QPushButton("Clear")
        btn_clear_all.setStyleSheet("""
            QPushButton { background-color: #3d3d3d; color: #ff6666; padding: 4px 8px; font-size: 9px; }
            QPushButton:hover { background-color: #ff6666; color: black; }
        """)
        btn_clear_all.clicked.connect(self._clear_all_measurements)
        measure_btn_row.addWidget(btn_clear_all)
        
        measure_col.addLayout(measure_btn_row)
        measure_col.addStretch()
        tools_row.addLayout(measure_col)
        
        # Vertical separator
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.VLine)
        v_sep.setStyleSheet("background-color: #3d3d3d;")
        v_sep.setFixedWidth(1)
        tools_row.addWidget(v_sep)
        
        # MIDDLE COLUMN: Crosshairs & 3D Options
        middle_col = QVBoxLayout()
        middle_col.setSpacing(5)
        
        crosshair_header = QLabel("MPR Crosshairs:")
        crosshair_header.setStyleSheet("color: #00bcd4; font-weight: bold; font-size: 11px;")
        middle_col.addWidget(crosshair_header)
        
        self.crosshair_checkbox = QCheckBox("Enable Crosshairs")
        self.crosshair_checkbox.setStyleSheet("""
            QCheckBox { color: #e0e0e0; font-size: 11px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { background-color: #2a2a2a; border: 1px solid #3d3d3d; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #00bcd4; border: 1px solid #00bcd4; border-radius: 3px; }
        """)
        self.crosshair_checkbox.stateChanged.connect(self._on_crosshair_toggle)
        middle_col.addWidget(self.crosshair_checkbox)
        
        self.crosshair_pos_label = QLabel("Position: --")
        self.crosshair_pos_label.setStyleSheet("color: #606060; font-size: 10px;")
        middle_col.addWidget(self.crosshair_pos_label)
        
        self.crosshair_manager.position_changed.connect(self._on_crosshair_position_display)
        
        middle_col.addSpacing(5)
        
        # 3D View Options
        view_3d_header = QLabel("3D View Options:")
        view_3d_header.setStyleSheet("color: #00bcd4; font-weight: bold; font-size: 11px;")
        middle_col.addWidget(view_3d_header)
        
        # Bounding Box Dimensions checkbox
        self.bbox_labels_checkbox = QCheckBox("Show Dimensions")
        self.bbox_labels_checkbox.setChecked(True)
        self.bbox_labels_checkbox.setStyleSheet("""
            QCheckBox { color: #e0e0e0; font-size: 10px; }
            QCheckBox::indicator { width: 14px; height: 14px; }
            QCheckBox::indicator:unchecked { background-color: #2a2a2a; border: 1px solid #3d3d3d; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #00bcd4; border: 1px solid #00bcd4; border-radius: 3px; }
        """)
        self.bbox_labels_checkbox.stateChanged.connect(self._on_bbox_labels_toggle)
        middle_col.addWidget(self.bbox_labels_checkbox)
        
        middle_col.addStretch()
        tools_row.addLayout(middle_col)
        
        # Vertical separator
        v_sep2 = QFrame()
        v_sep2.setFrameShape(QFrame.VLine)
        v_sep2.setStyleSheet("background-color: #3d3d3d;")
        v_sep2.setFixedWidth(1)
        tools_row.addWidget(v_sep2)
        
        # RIGHT COLUMN: Clipping Tool (NEW)
        clipping_col = QVBoxLayout()
        clipping_col.setSpacing(5)
        
        clipping_header = QLabel("✂️ Cutting Tool:")
        clipping_header.setStyleSheet("color: #00bcd4; font-weight: bold; font-size: 11px;")
        clipping_col.addWidget(clipping_header)
        
        self.clipping_checkbox = QCheckBox("Enable Clipping")
        self.clipping_checkbox.setStyleSheet("""
            QCheckBox { color: #e0e0e0; font-size: 11px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { background-color: #2a2a2a; border: 1px solid #3d3d3d; border-radius: 3px; }
            QCheckBox::indicator:checked { background-color: #ff6600; border: 1px solid #ff6600; border-radius: 3px; }
        """)
        self.clipping_checkbox.toggled.connect(self._on_clipping_toggle)
        clipping_col.addWidget(self.clipping_checkbox)
        
        # Orientation presets for clipping plane
        orient_label = QLabel("Plane Orientation:")
        orient_label.setStyleSheet("color: #808080; font-size: 10px;")
        clipping_col.addWidget(orient_label)
        
        self.clipping_orient_combo = QComboBox()
        self.clipping_orient_combo.addItems(["Axial (Z)", "Sagittal (X)", "Coronal (Y)"])
        self.clipping_orient_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3d3d3d;
                padding: 3px 8px;
                font-size: 10px;
                border-radius: 3px;
            }
            QComboBox:hover {
                border: 1px solid #ff6600;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #ff6600;
                font-size: 10px;
            }
        """)
        self.clipping_orient_combo.currentIndexChanged.connect(self._on_clipping_orientation_changed)
        clipping_col.addWidget(self.clipping_orient_combo)
        
        # Reset button
        btn_reset_clip = QPushButton("Reset Plane")
        btn_reset_clip.setStyleSheet("""
            QPushButton { background-color: #3d3d3d; color: #ff6600; padding: 4px 8px; font-size: 9px; }
            QPushButton:hover { background-color: #ff6600; color: black; }
        """)
        btn_reset_clip.clicked.connect(self._reset_clipping_plane)
        clipping_col.addWidget(btn_reset_clip)
        
        clipping_info = QLabel("Drag plane to cut\nvolume in 3D view")
        clipping_info.setStyleSheet("color: #505050; font-size: 9px;")
        clipping_col.addWidget(clipping_info)
        
        clipping_col.addStretch()
        tools_row.addLayout(clipping_col)
        
        layout.addLayout(tools_row)
        layout.addStretch()
        parent_layout.addWidget(panel)

    def _on_clipping_toggle(self, checked):
        """Enable/Disable clipping plane on 3D view."""
        if '3d' not in self.viewports:
            return
        
        self.viewports['3d'].set_clipping_enabled(checked)
        
        # Sync menu action if exists
        if hasattr(self, 'clipping_action'):
            self.clipping_action.setChecked(checked)
        
        if checked:
            self.statusBar().showMessage("Clipping enabled - drag the plane to cut the volume", 5000)
        else:
            self.statusBar().showMessage("Clipping disabled - full volume restored", 2000)

    def _on_clipping_orientation_changed(self, index):
        """Handle clipping plane orientation change."""
        if '3d' not in self.viewports:
            return
        
        orientations = ['axial', 'sagittal', 'coronal']
        if 0 <= index < len(orientations):
            self.viewports['3d'].set_clipping_plane_orientation(orientations[index])
            self.statusBar().showMessage(f"Clipping plane set to {orientations[index]} orientation", 2000)

    def _reset_clipping_plane(self):
        """Reset clipping plane to default position."""
        if '3d' not in self.viewports:
            return
        
        self.viewports['3d'].reset_clipping_plane()
        self.clipping_orient_combo.setCurrentIndex(0)  # Reset to Axial
        self.statusBar().showMessage("Clipping plane reset to center", 2000)

    def _on_bbox_labels_toggle(self, state):
        """Handle bounding box dimension labels toggle."""
        enabled = state == Qt.Checked
        
        if '3d' in self.viewports:
            self.viewports['3d'].set_bbox_labels_visible(enabled)
            
            # Sync menu action
            if hasattr(self, 'bbox_labels_action'):
                self.bbox_labels_action.blockSignals(True)
                self.bbox_labels_action.setChecked(enabled)
                self.bbox_labels_action.blockSignals(False)
            
            state_text = "visible" if enabled else "hidden"
            self.statusBar().showMessage(f"Dimension labels {state_text}", 2000)
    
    def _on_unit_changed(self, index):
        """Handle measurement unit change."""
        unit = 'mm' if index == 0 else 'px'
        
        # Sync menu actions
        if hasattr(self, 'mm_action'):
            self.mm_action.setChecked(unit == 'mm')
            self.px_action.setChecked(unit == 'px')
        
        for viewport in self.viewports.values():
            viewport.set_measurement_unit(unit)
        
        unit_name = "Millimeters" if unit == 'mm' else "Pixels"
        self.statusBar().showMessage(f"Measurement unit: {unit_name}", 2000)

    def _on_ruler_toggle(self, checked):
        """Enable/Disable measurement widget on ALL views including 3D."""
        for view_name, viewport in self.viewports.items():
            viewport.set_measurement_enabled(checked)
        
        # Sync menu action
        if hasattr(self, 'ruler_action'):
            self.ruler_action.setChecked(checked)
        
        if checked:
            if self.crosshair_checkbox.isChecked():
                self.crosshair_checkbox.setChecked(False)
            self.statusBar().showMessage("Ruler Mode: Click two points to measure. Repeat for multiple measurements.", 5000)
        else:
            self.statusBar().showMessage("Ruler Mode Disabled", 2000)
        
        self._update_measurement_count()

    def _clear_last_measurement(self):
        """Clear the last measurement from all viewports."""
        for viewport in self.viewports.values():
            viewport.clear_last_measurement()
        self._update_measurement_count()
        self.statusBar().showMessage("Last measurement cleared", 2000)

    def _clear_all_measurements(self):
        """Clear all measurements from all viewports."""
        for viewport in self.viewports.values():
            viewport.clear_all_measurements()
        self._update_measurement_count()
        self.statusBar().showMessage("All measurements cleared", 2000)

    def _update_measurement_count(self):
        """Update the measurement count display."""
        total = sum(vp.get_measurement_count() for vp in self.viewports.values())
        self.measurement_count_label.setText(f"Measurements: {total}")

    def _on_crosshair_toggle(self, state):
        """Handle crosshair enable/disable checkbox."""
        enabled = state == Qt.Checked
        
        # Sync menu action
        if hasattr(self, 'crosshair_action'):
            self.crosshair_action.setChecked(enabled)
        
        self.crosshair_manager.enabled = enabled
        
        for view_type, viewport in self.viewports.items():
            if view_type != '3d':
                viewport.set_crosshair_enabled(enabled)
        
        if enabled:
            self.statusBar().showMessage("Crosshairs enabled - scroll or click to navigate", 3000)
            if self.vtk_handler.is_loaded:
                x, y, z = self.crosshair_manager.current_center
                self.crosshair_manager.position_changed.emit(x, y, z)
        else:
            self.statusBar().showMessage("Crosshairs disabled", 2000)
            self.crosshair_pos_label.setText("Position: --")

    def _on_crosshair_position_display(self, x, y, z):
        """Update crosshair position display label."""
        self.crosshair_pos_label.setText(f"X:{x:.0f} Y:{y:.0f} Z:{z:.0f}")

    def create_menus(self):
        """Create menu bar with Camera menu."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        scan_action = QAction("Import Root Folder...", self)
        scan_action.setShortcut("Ctrl+O")
        scan_action.triggered.connect(self._trigger_smart_scan)
        file_menu.addAction(scan_action)
        
        import_action = QAction("Import Single DICOM Folder...", self)
        import_action.triggered.connect(self.import_dicom)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()

        save_action = QAction("Save Work...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_work)
        file_menu.addAction(save_action)

        load_action = QAction("Load Work...", self)
        load_action.setShortcut("Ctrl+L")
        load_action.triggered.connect(self.load_work)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        reset_action = QAction("Reset All Views", self)
        reset_action.setShortcut("Ctrl+R")
        reset_action.triggered.connect(self.reset_all_views)
        view_menu.addAction(reset_action)
        
        view_menu.addSeparator()
        
        toggle_browser_action = QAction("Toggle Smart Scan", self)
        toggle_browser_action.setShortcut("Ctrl+B")
        toggle_browser_action.triggered.connect(self._toggle_study_browser)
        view_menu.addAction(toggle_browser_action)

        view_menu.addSeparator()

        # === NEW: Bounding Box Toggle ===
        self.bounding_box_action = QAction("Show Bounding Box", self)
        self.bounding_box_action.setCheckable(True)
        self.bounding_box_action.setChecked(True)
        self.bounding_box_action.setShortcut("B")
        self.bounding_box_action.triggered.connect(self._toggle_bounding_box)
        view_menu.addAction(self.bounding_box_action)

        # === NEW: Dimension Labels Toggle ===
        self.bbox_labels_action = QAction("Show Dimension Labels (3D)", self)
        self.bbox_labels_action.setCheckable(True)
        self.bbox_labels_action.setChecked(True)
        self.bbox_labels_action.setShortcut("D")
        self.bbox_labels_action.triggered.connect(self._toggle_bbox_labels)
        view_menu.addAction(self.bbox_labels_action)

        # === NEW: Scale Rulers Toggle ===
        self.scale_rulers_action = QAction("Show Scale Rulers (3D)", self)
        self.scale_rulers_action.setCheckable(True)
        self.scale_rulers_action.setChecked(True)
        self.scale_rulers_action.setShortcut("K")
        self.scale_rulers_action.triggered.connect(self._toggle_scale_rulers)
        view_menu.addAction(self.scale_rulers_action)
        
        # ============ NEW: Camera Menu ============
        camera_menu = menubar.addMenu("Camera")
        
        # --- Camera Settings Submenu ---
        settings_submenu = camera_menu.addMenu("📷 Camera Settings")
        
        axial_settings = QAction("Axial View Settings...", self)
        axial_settings.triggered.connect(lambda: self._open_camera_settings('axial'))
        settings_submenu.addAction(axial_settings)
        
        sagittal_settings = QAction("Sagittal View Settings...", self)
        sagittal_settings.triggered.connect(lambda: self._open_camera_settings('sagittal'))
        settings_submenu.addAction(sagittal_settings)
        
        coronal_settings = QAction("Coronal View Settings...", self)
        coronal_settings.triggered.connect(lambda: self._open_camera_settings('coronal'))
        settings_submenu.addAction(coronal_settings)
        
        settings_submenu.addSeparator()
        
        vol_settings = QAction("3D Volume Settings...", self)
        vol_settings.triggered.connect(lambda: self._open_camera_settings('3d'))
        settings_submenu.addAction(vol_settings)
        
        camera_menu.addSeparator()
        
        # --- Projection Type Submenu (for 3D view) ---
        projection_submenu = camera_menu.addMenu("🎥 3D Projection Type")
        
        self.perspective_action = QAction("Perspective", self)
        self.perspective_action.setCheckable(True)
        self.perspective_action.setChecked(True)
        self.perspective_action.triggered.connect(lambda: self._set_3d_projection(False))
        projection_submenu.addAction(self.perspective_action)
        
        self.parallel_action = QAction("Parallel (Orthographic)", self)
        self.parallel_action.setCheckable(True)
        self.parallel_action.triggered.connect(lambda: self._set_3d_projection(True))
        projection_submenu.addAction(self.parallel_action)
        
        # Group projection actions
        projection_group = QActionGroup(self)
        projection_group.addAction(self.perspective_action)
        projection_group.addAction(self.parallel_action)
        projection_group.setExclusive(True)
        
        camera_menu.addSeparator()
        
        # --- 3D Camera Preset Views ---
        presets_submenu = camera_menu.addMenu("🎯 3D Preset Views")
        
        anterior_action = QAction("Anterior (Front)", self)
        anterior_action.setShortcut("A")
        anterior_action.triggered.connect(lambda: self._set_3d_preset_view('anterior'))
        presets_submenu.addAction(anterior_action)
        
        posterior_action = QAction("Posterior (Back)", self)
        posterior_action.setShortcut("P")
        posterior_action.triggered.connect(lambda: self._set_3d_preset_view('posterior'))
        presets_submenu.addAction(posterior_action)
        
        presets_submenu.addSeparator()
        
        left_action = QAction("Left", self)
        left_action.setShortcut("L")
        left_action.triggered.connect(lambda: self._set_3d_preset_view('left'))
        presets_submenu.addAction(left_action)
        
        right_action = QAction("Right", self)
        right_action.setShortcut("R")
        right_action.triggered.connect(lambda: self._set_3d_preset_view('right'))
        presets_submenu.addAction(right_action)
        
        presets_submenu.addSeparator()
        
        superior_action = QAction("Superior (Top)", self)
        superior_action.setShortcut("S")
        superior_action.triggered.connect(lambda: self._set_3d_preset_view('superior'))
        presets_submenu.addAction(superior_action)
        
        inferior_action = QAction("Inferior (Bottom)", self)
        inferior_action.setShortcut("I")
        inferior_action.triggered.connect(lambda: self._set_3d_preset_view('inferior'))
        presets_submenu.addAction(inferior_action)
        
        presets_submenu.addSeparator()
        
        isometric_action = QAction("Isometric", self)
        isometric_action.setShortcut("Ctrl+I")
        isometric_action.triggered.connect(lambda: self._set_3d_preset_view('isometric'))
        presets_submenu.addAction(isometric_action)
        
        camera_menu.addSeparator()
        
        # --- Field of View Quick Adjust ---
        fov_submenu = camera_menu.addMenu("🔍 Field of View (3D)")
        
        fov_15 = QAction("Narrow (15°)", self)
        fov_15.triggered.connect(lambda: self._set_3d_fov(15))
        fov_submenu.addAction(fov_15)
        
        fov_30 = QAction("Default (30°)", self)
        fov_30.triggered.connect(lambda: self._set_3d_fov(30))
        fov_submenu.addAction(fov_30)
        
        fov_60 = QAction("Wide (60°)", self)
        fov_60.triggered.connect(lambda: self._set_3d_fov(60))
        fov_submenu.addAction(fov_60)
        
        fov_90 = QAction("Ultra Wide (90°)", self)
        fov_90.triggered.connect(lambda: self._set_3d_fov(90))
        fov_submenu.addAction(fov_90)
        
        camera_menu.addSeparator()
        
        # --- Reset Cameras ---
        reset_3d_action = QAction("Reset 3D Camera", self)
        reset_3d_action.setShortcut("Ctrl+3")
        reset_3d_action.triggered.connect(lambda: self.viewports['3d'].reset_camera() if '3d' in self.viewports else None)
        camera_menu.addAction(reset_3d_action)
        
        reset_2d_action = QAction("Reset All 2D Cameras", self)
        reset_2d_action.setShortcut("Ctrl+2")
        reset_2d_action.triggered.connect(self._reset_2d_cameras)
        camera_menu.addAction(reset_2d_action)
        
        # Tools menu (NEW - moved tools here)
        tools_menu = menubar.addMenu("Tools")
        
        # Measurement tools
        measurement_submenu = tools_menu.addMenu("📏 Measurement")
        
        self.ruler_action = QAction("Enable Ruler Mode", self)
        self.ruler_action.setCheckable(True)
        self.ruler_action.setShortcut("M")
        self.ruler_action.triggered.connect(self._toggle_ruler_from_menu)
        measurement_submenu.addAction(self.ruler_action)
        
        measurement_submenu.addSeparator()
        
        clear_last_action = QAction("Clear Last Measurement", self)
        clear_last_action.setShortcut("Delete")
        clear_last_action.triggered.connect(self._clear_last_measurement)
        measurement_submenu.addAction(clear_last_action)
        
        clear_all_action = QAction("Clear All Measurements", self)
        clear_all_action.setShortcut("Ctrl+Delete")
        clear_all_action.triggered.connect(self._clear_all_measurements)
        measurement_submenu.addAction(clear_all_action)
        
        measurement_submenu.addSeparator()
        
        # Unit selection
        unit_submenu = measurement_submenu.addMenu("Unit")
        
        self.mm_action = QAction("Millimeters (mm)", self)
        self.mm_action.setCheckable(True)
        self.mm_action.setChecked(True)
        self.mm_action.triggered.connect(lambda: self._set_measurement_unit('mm'))
        unit_submenu.addAction(self.mm_action)
        
        self.px_action = QAction("Pixels (px)", self)
        self.px_action.setCheckable(True)
        self.px_action.triggered.connect(lambda: self._set_measurement_unit('px'))
        unit_submenu.addAction(self.px_action)
        
        unit_group = QActionGroup(self)
        unit_group.addAction(self.mm_action)
        unit_group.addAction(self.px_action)
        unit_group.setExclusive(True)
        
        tools_menu.addSeparator()

        # Clipping Tool
        clipping_submenu = tools_menu.addMenu("✂️ Clipping Plane")
        
        self.clipping_action = QAction("Enable Clipping", self)
        self.clipping_action.setCheckable(True)
        self.clipping_action.setShortcut("X")
        self.clipping_action.triggered.connect(self._toggle_clipping_from_menu)
        clipping_submenu.addAction(self.clipping_action)
        
        clipping_submenu.addSeparator()
        
        clip_axial_action = QAction("Axial Plane (Z)", self)
        clip_axial_action.triggered.connect(lambda: self._set_clipping_orientation('axial'))
        clipping_submenu.addAction(clip_axial_action)
        
        clip_sagittal_action = QAction("Sagittal Plane (X)", self)
        clip_sagittal_action.triggered.connect(lambda: self._set_clipping_orientation('sagittal'))
        clipping_submenu.addAction(clip_sagittal_action)
        
        clip_coronal_action = QAction("Coronal Plane (Y)", self)
        clip_coronal_action.triggered.connect(lambda: self._set_clipping_orientation('coronal'))
        clipping_submenu.addAction(clip_coronal_action)
        
        clipping_submenu.addSeparator()
        
        reset_clip_action = QAction("Reset Clipping Plane", self)
        reset_clip_action.triggered.connect(self._reset_clipping_plane)
        clipping_submenu.addAction(reset_clip_action)
        
        # Crosshairs
        self.crosshair_action = QAction("Enable Crosshairs", self)
        self.crosshair_action.setCheckable(True)
        self.crosshair_action.setShortcut("C")
        self.crosshair_action.triggered.connect(self._toggle_crosshair_from_menu)
        tools_menu.addAction(self.crosshair_action)
        
        # Presets menu
        presets_menu = menubar.addMenu("Presets")
        
        bone_action = QAction("Bone", self)
        bone_action.triggered.connect(lambda: self.apply_tissue_preset('bone'))
        presets_menu.addAction(bone_action)
        
        soft_action = QAction("Soft Tissue", self)
        soft_action.triggered.connect(lambda: self.apply_tissue_preset('soft'))
        presets_menu.addAction(soft_action)
        
        muscle_action = QAction("Muscle", self)
        muscle_action.triggered.connect(lambda: self.apply_tissue_preset('muscle'))
        presets_menu.addAction(muscle_action)
        
        presets_menu.addSeparator()
        
        auto_action = QAction("Auto-Detect", self)
        auto_action.triggered.connect(lambda: self.apply_tissue_preset('auto'))
        presets_menu.addAction(auto_action)
        
        mri_action = QAction("X-Ray", self)
        mri_action.triggered.connect(lambda: self.apply_tissue_preset('xray'))
        presets_menu.addAction(mri_action)
        
        xray_action = QAction("MRI", self)
        xray_action.triggered.connect(lambda: self.apply_tissue_preset('mri'))
        presets_menu.addAction(xray_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        help_action = QAction("Help", self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _toggle_clipping_from_menu(self, checked):
        """Toggle clipping from menu."""
        self.clipping_checkbox.setChecked(checked)
        self.clipping_action.setChecked(checked)

    def _set_clipping_orientation(self, orientation):
        """Set clipping orientation from menu."""
        orientations = {'axial': 0, 'sagittal': 1, 'coronal': 2}
        if orientation in orientations:
            self.clipping_orient_combo.setCurrentIndex(orientations[orientation])


    def _toggle_bbox_labels(self, checked):
        """Toggle the bounding box dimension labels visibility on 3D view."""
        if '3d' in self.viewports:
            self.viewports['3d'].set_bbox_labels_visible(checked)
            # Sync checkbox in tools panel
            self.bbox_labels_checkbox.blockSignals(True)
            self.bbox_labels_checkbox.setChecked(checked)
            self.bbox_labels_checkbox.blockSignals(False)
            state = "visible" if checked else "hidden"
            self.statusBar().showMessage(f"Dimension labels {state}", 2000)

    def _toggle_scale_rulers(self, checked):
        """Toggle the scale rulers visibility on 3D view."""
        if '3d' in self.viewports:
            self.viewports['3d'].set_scale_rulers_visible(checked)
            state = "visible" if checked else "hidden"
            self.statusBar().showMessage(f"Scale rulers {state}", 2000)

    def _open_camera_settings(self, view_type):
        """Open camera settings dialog for a specific view."""
        if view_type not in self.viewports:
            return
        
        view_names = {
            'axial': 'Axial View',
            'sagittal': 'Sagittal View',
            'coronal': 'Coronal View',
            '3d': '3D Volume View'
        }
        
        dialog = CameraSettingsDialog(self, self.viewports[view_type], view_names.get(view_type, view_type))
        dialog.exec_()
    
    def _set_3d_projection(self, parallel):
        """Set 3D view projection type."""
        if '3d' not in self.viewports:
            return
        
        cam = self.viewports['3d'].renderer.GetActiveCamera()
        cam.SetParallelProjection(parallel)
        
        # Update menu checkmarks
        self.perspective_action.setChecked(not parallel)
        self.parallel_action.setChecked(parallel)
        
        self.viewports['3d'].renderer.ResetCameraClippingRange()
        self.viewports['3d'].render()
        
        proj_name = "Parallel (Orthographic)" if parallel else "Perspective"
        self.statusBar().showMessage(f"3D Projection: {proj_name}", 2000)
    
    def _set_3d_preset_view(self, preset):
        """Set 3D camera to a preset viewing position."""
        if '3d' not in self.viewports:
            return
        
        viewport = self.viewports['3d']
        cam = viewport.renderer.GetActiveCamera()
        
        # Get the center of the volume
        if viewport.image_data_ref:
            bounds = viewport.image_data_ref.GetBounds()
            center = [
                (bounds[0] + bounds[1]) / 2,
                (bounds[2] + bounds[3]) / 2,
                (bounds[4] + bounds[5]) / 2
            ]
            # Calculate a reasonable distance based on volume size
            size = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
            distance = size * 2
        else:
            center = [0, 0, 0]
            distance = 500
        
        # Set focal point to center
        cam.SetFocalPoint(center)
        
        # Set camera position based on preset
        if preset == 'anterior':
            cam.SetPosition(center[0], center[1] - distance, center[2])
            cam.SetViewUp(0, 0, 1)
        elif preset == 'posterior':
            cam.SetPosition(center[0], center[1] + distance, center[2])
            cam.SetViewUp(0, 0, 1)
        elif preset == 'left':
            cam.SetPosition(center[0] - distance, center[1], center[2])
            cam.SetViewUp(0, 0, 1)
        elif preset == 'right':
            cam.SetPosition(center[0] + distance, center[1], center[2])
            cam.SetViewUp(0, 0, 1)
        elif preset == 'superior':
            cam.SetPosition(center[0], center[1], center[2] + distance)
            cam.SetViewUp(0, 1, 0)
        elif preset == 'inferior':
            cam.SetPosition(center[0], center[1], center[2] - distance)
            cam.SetViewUp(0, -1, 0)
        elif preset == 'isometric':
            cam.SetPosition(
                center[0] + distance * 0.577,
                center[1] - distance * 0.577,
                center[2] + distance * 0.577
            )
            cam.SetViewUp(0, 0, 1)
        
        viewport.renderer.ResetCameraClippingRange()
        viewport.render()
        
        preset_names = {
            'anterior': 'Anterior (Front)',
            'posterior': 'Posterior (Back)',
            'left': 'Left',
            'right': 'Right',
            'superior': 'Superior (Top)',
            'inferior': 'Inferior (Bottom)',
            'isometric': 'Isometric'
        }
        self.statusBar().showMessage(f"3D View: {preset_names.get(preset, preset)}", 2000)
    
    def _set_3d_fov(self, fov):
        """Set 3D view field of view."""
        if '3d' not in self.viewports:
            return
        
        cam = self.viewports['3d'].renderer.GetActiveCamera()
        cam.SetViewAngle(fov)
        self.viewports['3d'].render()
        
        self.statusBar().showMessage(f"3D Field of View: {fov}°", 2000)
    
    def _reset_2d_cameras(self):
        """Reset all 2D view cameras."""
        for view_type in ['axial', 'sagittal', 'coronal']:
            if view_type in self.viewports:
                self.viewports[view_type].reset_camera()
        self.statusBar().showMessage("All 2D cameras reset", 2000)
    
    def _toggle_ruler_from_menu(self, checked):
        """Toggle ruler mode from menu."""
        self.ruler_checkbox.setChecked(checked)
        self.ruler_action.setChecked(checked)
    
    def _toggle_crosshair_from_menu(self, checked):
        """Toggle crosshairs from menu."""
        self.crosshair_checkbox.setChecked(checked)
        self.crosshair_action.setChecked(checked)
    
    def _set_measurement_unit(self, unit):
        """Set measurement unit from menu."""
        index = 0 if unit == 'mm' else 1
        self.unit_combo.setCurrentIndex(index)
        self.mm_action.setChecked(unit == 'mm')
        self.px_action.setChecked(unit == 'px')
    
    def create_custom_toolbar(self):
        """Create toolbar with camera controls."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        scan_btn = QAction("📁 Smart Scan", self)
        scan_btn.setToolTip("Recursively scan a directory for DICOM series")
        scan_btn.triggered.connect(self._trigger_smart_scan)
        toolbar.addAction(scan_btn)
        
        import_btn = QAction("📂 Import Folder", self)
        import_btn.setToolTip("Import a single DICOM folder")
        import_btn.triggered.connect(self.import_dicom)
        toolbar.addAction(import_btn)
        
        toolbar.addSeparator()
        
        # Camera preset buttons
        cam_label = QLabel(" 3D View: ")
        cam_label.setStyleSheet("color: #808080;")
        toolbar.addWidget(cam_label)
        
        front_btn = QAction("Front", self)
        front_btn.setToolTip("Anterior view (A)")
        front_btn.triggered.connect(lambda: self._set_3d_preset_view('anterior'))
        toolbar.addAction(front_btn)
        
        back_btn = QAction("Back", self)
        back_btn.setToolTip("Posterior view (P)")
        back_btn.triggered.connect(lambda: self._set_3d_preset_view('posterior'))
        toolbar.addAction(back_btn)
        
        left_btn = QAction("Left", self)
        left_btn.setToolTip("Left view (L)")
        left_btn.triggered.connect(lambda: self._set_3d_preset_view('left'))
        toolbar.addAction(left_btn)
        
        right_btn = QAction("Right", self)
        right_btn.setToolTip("Right view (R)")
        right_btn.triggered.connect(lambda: self._set_3d_preset_view('right'))
        toolbar.addAction(right_btn)
        
        top_btn = QAction("Top", self)
        top_btn.setToolTip("Superior view (S)")
        top_btn.triggered.connect(lambda: self._set_3d_preset_view('superior'))
        toolbar.addAction(top_btn)
        
        iso_btn = QAction("Iso", self)
        iso_btn.setToolTip("Isometric view (Ctrl+I)")
        iso_btn.triggered.connect(lambda: self._set_3d_preset_view('isometric'))
        toolbar.addAction(iso_btn)
        
        toolbar.addSeparator()
        
        # Projection toggle
        self.proj_toggle_btn = QAction("📷 Persp", self)
        self.proj_toggle_btn.setToolTip("Toggle Perspective/Orthographic projection")
        self.proj_toggle_btn.setCheckable(True)
        self.proj_toggle_btn.triggered.connect(self._toggle_projection_toolbar)
        toolbar.addAction(self.proj_toggle_btn)
        
        toolbar.addSeparator()
        
        reset_all_btn = QAction("🔄 Reset All", self)
        reset_all_btn.setToolTip("Reset all viewport cameras")
        reset_all_btn.triggered.connect(self.reset_all_views)
        toolbar.addAction(reset_all_btn)
        
        reset_3d_btn = QAction("🔄 Reset 3D", self)
        reset_3d_btn.setToolTip("Reset the 3D viewport camera")
        reset_3d_btn.triggered.connect(lambda: self.viewports['3d'].reset_camera() if '3d' in self.viewports else None)
        toolbar.addAction(reset_3d_btn)
     
    def _toggle_projection_toolbar(self, checked):
        """Toggle projection type from toolbar button."""
        if '3d' not in self.viewports:
            return
        
        # checked = True means switch to Orthographic
        self._set_3d_projection(checked)
        
        # Update button text
        if checked:
            self.proj_toggle_btn.setText("📷 Ortho")
        else:
            self.proj_toggle_btn.setText("📷 Persp")
    
    def _trigger_smart_scan(self):
        """Trigger the smart scan from the study browser."""
        self.study_browser._on_scan_clicked()
    
    def _toggle_study_browser(self):
        """Toggle the visibility of the study browser dock."""
        for dock in self.findChildren(QDockWidget):
            if dock.windowTitle() == "Smart Scan":
                dock.setVisible(not dock.isVisible())
                break

    def _toggle_bounding_box(self, checked):
        """Toggle the bounding box visibility on 3D view."""
        if '3d' in self.viewports:
            self.viewports['3d'].set_bounding_box_visible(checked)
            state = "visible" if checked else "hidden"
            self.statusBar().showMessage(f"Bounding box {state}", 2000)
    
    def _on_series_selected(self, series_info):
        """Handle series selection from study browser."""
        print(f"Selected series: {series_info.get('series_description', 'Unknown')}")
        self.current_series_info = series_info
        
        # Clear current data
        self.vtk_handler.clear()
        for viewport in self.viewports.values():
            viewport.clear()
        
        # Load the selected series
        file_paths = series_info.get('file_paths', [])
        if not file_paths:
            QMessageBox.warning(self, "Error", "No files found for this series.")
            return
        
        self.current_dicom_path = os.path.dirname(file_paths[0])

        # Show loading indicator
        self.statusBar().showMessage(f"Loading {len(file_paths)} images...")
        QApplication.processEvents()
        
        try:
            if self.vtk_handler.load_from_file_list(file_paths):
                image_data = self.vtk_handler.imageData
                
                if image_data is None:
                    QMessageBox.warning(self, "Error", "Failed to create volume from series.")
                    return
                
                dims = image_data.GetDimensions()
                
                # Initialize crosshair manager with image bounds
                bounds = image_data.GetBounds()
                self.crosshair_manager.set_image_bounds(bounds)
                
                # Prepare metadata for overlays
                metadata = {
                    'patient_name': series_info.get('patient_name', 'Anonymous'),
                    'patient_id': series_info.get('series_uid', '')[:20] if series_info.get('series_uid') else '',
                    'study_date': series_info.get('study_date', ''),
                    'modality': series_info.get('modality', 'Unknown'),
                    'series_description': series_info.get('series_description', '')
                }
                
                # Setup views
                self.viewports['axial'].setup_2d_view(image_data, 'axial')
                self.viewports['sagittal'].setup_2d_view(image_data, 'sagittal')
                self.viewports['coronal'].setup_2d_view(image_data, 'coronal')
                
                if not self.vtk_handler.is_2d:
                    self.viewports['3d'].setup_3d_view(image_data, self.vtk_handler.volumeProperty)
                else:
                    if self.viewports['3d'].corner_annotation:
                        self.viewports['3d'].corner_annotation.SetText(2, "3D VOLUME\n(Requires 3D data)")
                
                # Update metadata overlays for all viewports
                for viewport in self.viewports.values():
                    viewport.update_metadata_overlay(metadata)
                
                # Apply current crosshair state
                crosshair_enabled = self.crosshair_checkbox.isChecked()
                for view_type, viewport in self.viewports.items():
                    if view_type != '3d':
                        viewport.set_crosshair_enabled(crosshair_enabled)
                
                for viewport in self.viewports.values():
                    viewport.render()
                
                # Update slice sliders
                self._update_slice_sliders()
                
                # Update UI
                desc = series_info.get('series_description', 'Unknown')
                modality = series_info.get('modality', 'Unknown')
                num_images = series_info.get('num_images', 0)
                
                self.dataset_combo.clear()
                self.dataset_combo.addItem(desc)
                
                # Update series info label
                info_text = f"Modality: {modality}\n"
                info_text += f"Images: {num_images}\n"
                info_text += f"Dimensions: {dims[0]}×{dims[1]}×{dims[2]}"
                self.series_info_label.setText(info_text)
                self.series_info_label.setStyleSheet("color: #00bcd4; font-size: 10px;")
                
                self.statusBar().showMessage(f"Loaded: {desc} ({dims[0]}×{dims[1]}×{dims[2]})", 5000)
            else:
                QMessageBox.warning(self, "Error", "Failed to load DICOM series.")
                self.statusBar().showMessage("Load failed", 3000)
                
        except Exception as e:
            print(f"Error loading series: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load series:\n{str(e)}")
            self.statusBar().showMessage("Load failed", 3000)
    
    def import_dicom(self):
        """Open file dialog to import a single DICOM directory."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select DICOM Directory",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if directory:
            self.load_dicom_data(directory)
    
    def load_dicom_data(self, path):
        """Load DICOM data from a single directory and setup all viewports."""
        print(f"Loading DICOM from: {path}")
        
        try:
            # Clear current data
            self.vtk_handler.clear()
            for viewport in self.viewports.values():
                viewport.clear()
            
            self.statusBar().showMessage(f"Loading from {path}...")
            QApplication.processEvents()
            
            if self.vtk_handler.load_dicom(path):
                image_data = self.vtk_handler.imageData
                
                if image_data is None:
                    QMessageBox.warning(self, "Error", "Failed to load image data")
                    return
                
                dims = image_data.GetDimensions()
                print(f"Image data dimensions: {dims}")
                
                # Initialize crosshair manager with image bounds
                bounds = image_data.GetBounds()
                self.crosshair_manager.set_image_bounds(bounds)
                
                # Prepare metadata for overlays
                folder_name = os.path.basename(path)
                metadata = {
                    'patient_name': folder_name,
                    'patient_id': '',
                    'study_date': '',
                    'modality': 'CT',
                    'series_description': folder_name
                }
                
                # Setup 2D views
                self.viewports['axial'].setup_2d_view(image_data, 'axial')
                self.viewports['sagittal'].setup_2d_view(image_data, 'sagittal')
                self.viewports['coronal'].setup_2d_view(image_data, 'coronal')
                
                # Setup 3D view only if we have depth
                if not self.vtk_handler.is_2d:
                    self.viewports['3d'].setup_3d_view(image_data, self.vtk_handler.volumeProperty)
                else:
                    if self.viewports['3d'].corner_annotation:
                        self.viewports['3d'].corner_annotation.SetText(2, "3D VOLUME\n(Requires 3D data)")
                
                # Update metadata overlays for all viewports
                for viewport in self.viewports.values():
                    viewport.update_metadata_overlay(metadata)
                
                # Apply current crosshair state
                crosshair_enabled = self.crosshair_checkbox.isChecked()
                for view_type, viewport in self.viewports.items():
                    if view_type != '3d':
                        viewport.set_crosshair_enabled(crosshair_enabled)
                
                # Render all viewports
                for viewport in self.viewports.values():
                    viewport.render()
                
                # Update slice sliders
                self._update_slice_sliders()
                
                # Update UI
                self.current_dicom_path = path
                self.dataset_combo.clear()
                self.dataset_combo.addItem(folder_name)
                
                # Update series info label
                info_text = f"Folder: {folder_name}\n"
                info_text += f"Dimensions: {dims[0]}×{dims[1]}×{dims[2]}"
                self.series_info_label.setText(info_text)
                self.series_info_label.setStyleSheet("color: #00bcd4; font-size: 10px;")
                
                if self.vtk_handler.is_2d:
                    self.statusBar().showMessage(f"Loaded 2D: {folder_name}", 5000)
                else:
                    self.statusBar().showMessage(f"Loaded 3D: {folder_name} ({dims[0]}×{dims[1]}×{dims[2]})", 5000)
            else:
                QMessageBox.warning(self, "Error", f"Failed to load DICOM from:\n{path}")
                self.statusBar().showMessage("Load failed", 3000)
                
        except Exception as e:
            print(f"Error in load_dicom_data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load DICOM:\n{str(e)}")
            self.statusBar().showMessage("Load failed", 3000)
    
    def rotate_3d_view(self, axis, angle):
        """Rotate the 3D viewport camera."""
        try:
            if '3d' in self.viewports:
                cam = self.viewports['3d'].renderer.GetActiveCamera()
                if axis == 'x':
                    cam.Elevation(angle)
                elif axis == 'y':
                    cam.Azimuth(angle)
                self.viewports['3d'].renderer.ResetCameraClippingRange()
                self.viewports['3d'].render()
        except Exception as e:
            print(f"Rotation error: {e}")
    
    def reset_all_views(self):
        """Reset all viewport cameras."""
        for viewport in self.viewports.values():
            viewport.reset_camera()
        self.statusBar().showMessage("All views reset", 2000)
    
    def on_adjustment_changed(self, key, value):
        """Handle adjustment slider changes."""
        if not self.vtk_handler.is_loaded:
            return
        
        try:
            prop = self.vtk_handler.volumeProperty
            normalized = value / 100.0
            
            if key == 'ambient':
                prop.SetAmbient(normalized)
            elif key == 'diffuse':
                prop.SetDiffuse(normalized)
            elif key == 'specular':
                prop.SetSpecular(normalized)
            elif key == 'specular_power':
                # Specular Power: 1-128 range (direct value, not normalized)
                # Higher = sharper/glossier reflection, Lower = duller/matte
                prop.SetSpecularPower(float(value))
            elif key == 'global_opacity':
                # Global Opacity: Scale the entire opacity transfer function
                # We'll use a scalar opacity unit distance approach
                # Lower value = more transparent, Higher = more opaque
                # This affects how quickly opacity accumulates through the volume
                if normalized > 0:
                    # ScalarOpacityUnitDistance: smaller = more opaque
                    # We invert and scale: 100% opacity -> small distance, 0% -> large distance
                    unit_distance = 1.0 / (normalized + 0.01)  # Avoid division by zero
                    prop.SetScalarOpacityUnitDistance(unit_distance)
                else:
                    prop.SetScalarOpacityUnitDistance(100.0)  # Very transparent
            elif key == 'window_width':
                # Window Width (Contrast) for 2D views
                # Maps 0-100 slider to reasonable window width range
                # 0 = narrow (high contrast), 100 = wide (low contrast, more gray levels)
                if self.vtk_handler.imageData:
                    scalar_range = self.vtk_handler.imageData.GetScalarRange()
                    data_range = scalar_range[1] - scalar_range[0]
                    # Map slider 0-100 to 10%-200% of data range
                    min_width = data_range * 0.1
                    max_width = data_range * 2.0
                    window = min_width + (value / 100.0) * (max_width - min_width)
                    
                    for view_type in ['axial', 'sagittal', 'coronal']:
                        if view_type in self.viewports:
                            vp = self.viewports[view_type]
                            if vp.image_slice:
                                current_level = vp.image_slice.GetProperty().GetColorLevel()
                                vp.image_slice.GetProperty().SetColorWindow(window)
                                vp._update_slice_text()
                                vp.render()
            elif key == 'window_level':
                # Window Level (Brightness) for 2D views
                # Maps 0-100 slider to the data range
                if self.vtk_handler.imageData:
                    scalar_range = self.vtk_handler.imageData.GetScalarRange()
                    min_val = scalar_range[0]
                    max_val = scalar_range[1]
                    # Map slider 0-100 to min-max of data range
                    level = min_val + (value / 100.0) * (max_val - min_val)
                    
                    for view_type in ['axial', 'sagittal', 'coronal']:
                        if view_type in self.viewports:
                            vp = self.viewports[view_type]
                            if vp.image_slice:
                                vp.image_slice.GetProperty().SetColorLevel(level)
                                vp._update_slice_text()
                                vp.render()
            
            # Render 3D view for volume property changes
            if key in ['ambient', 'diffuse', 'specular', 'specular_power', 'global_opacity']:
                if '3d' in self.viewports:
                    self.viewports['3d'].render()
                    
        except Exception as e:
            print(f"Adjustment error: {e}")

    
    def apply_tissue_preset(self, preset):
        """Apply tissue visualization preset."""
        if not self.vtk_handler.is_loaded:
            QMessageBox.warning(self, "Warning", "Please load DICOM data first.")
            return
        
        try:
            # Store current preset for saving
            self.current_preset = preset
            
            # Update button styles to show selection
            self._update_preset_button_styles(preset)
            
            if preset == 'bone':
                self.vtk_handler.setup_bone_preset()
                self.statusBar().showMessage("Applied: Bone preset", 2000)
            elif preset == 'soft':
                self.vtk_handler.setup_soft_tissue_preset()
                self.statusBar().showMessage("Applied: Soft tissue preset", 2000)
            elif preset == 'muscle':
                self.vtk_handler.setup_muscle_preset()
                self.statusBar().showMessage("Applied: Muscle preset", 2000)
            elif preset == 'auto':
                self.vtk_handler.setup_auto_preset()
                self.statusBar().showMessage("Applied: Auto-detected preset", 2000)
            elif preset == 'xray':
                self.vtk_handler.setup_mri_preset()
                self.statusBar().showMessage("Applied: X-Ray preset", 2000)
            elif preset == 'mri':
                self.vtk_handler.setup_xray_preset()
                self.statusBar().showMessage("Applied: MRI preset", 2000)
            
            # Render 3D view
            if '3d' in self.viewports:
                self.viewports['3d'].render()
        except Exception as e:
            print(f"Preset error: {e}")
    
    def change_background(self):
        """Toggle background color for all viewports."""
        try:
            for viewport in self.viewports.values():
                current = viewport.renderer.GetBackground()
                if current[0] < 0.2:
                    viewport.renderer.SetBackground(0.2, 0.2, 0.25)
                else:
                    viewport.renderer.SetBackground(0.1, 0.1, 0.1)
                viewport.render()
        except Exception as e:
            print(f"Background change error: {e}")
    
    def show_help(self):
        """Show help dialog."""
        dialog = HelpDialog(self)
        dialog.exec_()
    
    def show_about(self):
        """Show about dialog."""
        about_text = """<h2>Medical DICOM Visualizer</h2>
        <p><b>Version 2.0 - Smart Scan Edition</b></p>
        <hr>
        <h3>Features:</h3>
        <ul>
            <li>📁 <b>Smart Scan:</b> Recursive DICOM directory scanning</li>
            <li>📋 <b>Smart Scan:</b> Series grouping with thumbnails</li>
            <li>🖼️ <b>2×2 MPR View:</b> Axial, Sagittal, Coronal, 3D</li>
            <li>🎨 <b>Tissue Presets:</b> Bone, Soft Tissue, Muscle</li>
            <li>🔧 <b>Adjustments:</b> Window/Level, Lighting</li>
        </ul>
        <hr>
        <p><b>Libraries:</b> PyQt5, VTK, pydicom, NumPy</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

    def save_work(self):
        """Save the current session state to a JSON file."""
        if not self.vtk_handler.is_loaded:
            QMessageBox.warning(self, "Save Error", "No data loaded to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Work", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        # Store current preset if set
        current_preset = getattr(self, 'current_preset', 'bone')
        
        # Get current measurement unit
        measurement_unit = 'mm' if self.unit_combo.currentIndex() == 0 else 'px'
        
        # --- Save Series UID and File Paths ---
        series_uid = None
        file_paths = []
        if self.current_series_info:
            series_uid = self.current_series_info.get('series_uid')
            file_paths = self.current_series_info.get('file_paths', [])
            
        state = {
            "dicom_path": self.current_dicom_path,
            "series_uid": series_uid,
            "file_paths": file_paths,
            "preset": current_preset,
            "colormap": getattr(self, 'current_colormap', 'gray'),
            "measurement_unit": measurement_unit,
            "adjustments": {k: s.value() for k, s in self.adjustment_sliders.items()},
            "crosshair": {
                "enabled": self.crosshair_checkbox.isChecked(),
                "center": list(self.crosshair_manager.current_center)
            },
            "viewports": {}
        }
        
        # === SAVE CLIPPING PLANE STATE ===
        if '3d' in self.viewports:
            vp_3d = self.viewports['3d']
            clipping_state = {
                "enabled": vp_3d.clipping_enabled,
                "orientation_index": self.clipping_orient_combo.currentIndex()
            }
            # Save plane position and normal if widget exists
            if vp_3d.clipping_plane_widget and vp_3d.clipping_plane:
                try:
                    rep = vp_3d.clipping_plane_widget.GetRepresentation()
                    origin = [0.0, 0.0, 0.0]
                    normal = [0.0, 0.0, 0.0]
                    rep.GetOrigin(origin)
                    rep.GetNormal(normal)
                    clipping_state["origin"] = origin
                    clipping_state["normal"] = normal
                except Exception as e:
                    print(f"Warning: Could not save clipping plane position: {e}")
            state["clipping"] = clipping_state
        
        # === SAVE VIEWPORT STATES ===
        for name, vp in self.viewports.items():
            cam = vp.renderer.GetActiveCamera()
            vp_state = {
                "camera": {
                    "position": list(cam.GetPosition()),
                    "focal_point": list(cam.GetFocalPoint()),
                    "view_up": list(cam.GetViewUp()),
                    "parallel_scale": cam.GetParallelScale(),
                    "clipping_range": list(cam.GetClippingRange()),
                    "view_angle": cam.GetViewAngle(),
                    "parallel_projection": cam.GetParallelProjection()
                },
                "measurements": vp.get_measurements_data(),
                "current_slice": vp.current_slice
            }
            
            # Save window/level for 2D views
            if name != '3d' and vp.image_slice:
                prop = vp.image_slice.GetProperty()
                vp_state["window"] = prop.GetColorWindow()
                vp_state["level"] = prop.GetColorLevel()
            
            # Save 3D-specific settings
            if name == '3d':
                vp_state["bounding_box_visible"] = getattr(vp, 'bounding_box_visible', True)
                vp_state["bbox_labels_visible"] = getattr(vp, 'bbox_labels_visible', True)
                if vp.legend_scale_actor:
                    vp_state["scale_rulers_visible"] = vp.legend_scale_actor.GetVisibility()
            
            state["viewports"][name] = vp_state
        
        # === SAVE UI CHECKBOX STATES ===
        state["ui_state"] = {
            "bbox_labels_checked": self.bbox_labels_checkbox.isChecked(),
            "ruler_enabled": self.ruler_checkbox.isChecked(),
            "bounding_box_action_checked": self.bounding_box_action.isChecked() if hasattr(self, 'bounding_box_action') else True,
            "scale_rulers_action_checked": self.scale_rulers_action.isChecked() if hasattr(self, 'scale_rulers_action') else True
        }
            
        try:
            with open(file_path, 'w') as f:
                json.dump(state, f, indent=4)
            self.statusBar().showMessage(f"Work saved to {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file: {e}")

    def load_work(self):
        """Load a session state from a JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Work", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            # 1. Load Data
            file_paths = state.get("file_paths", [])
            path = state.get("dicom_path")
            series_uid = state.get("series_uid")
            
            data_loaded = False
            
            # Option A: Load from specific file list (Best for Smart Scan results)
            if file_paths and len(file_paths) > 0 and os.path.exists(file_paths[0]):
                self.statusBar().showMessage(f"Restoring series {series_uid}...")
                QApplication.processEvents()
                
                self.vtk_handler.clear()
                for viewport in self.viewports.values():
                    viewport.clear()
                
                if self.vtk_handler.load_from_file_list(file_paths):
                    image_data = self.vtk_handler.imageData
                    self.crosshair_manager.set_image_bounds(image_data.GetBounds())
                    
                    metadata = {
                        'patient_name': 'Restored',
                        'series_uid': series_uid or '',
                        'modality': 'Restored'
                    }
                    
                    self.viewports['axial'].setup_2d_view(image_data, 'axial')
                    self.viewports['sagittal'].setup_2d_view(image_data, 'sagittal')
                    self.viewports['coronal'].setup_2d_view(image_data, 'coronal')
                    
                    if not self.vtk_handler.is_2d:
                        self.viewports['3d'].setup_3d_view(image_data, self.vtk_handler.volumeProperty)
                    
                    for viewport in self.viewports.values():
                        viewport.update_metadata_overlay(metadata)
                        viewport.render()
                        
                    self.current_dicom_path = os.path.dirname(file_paths[0])
                    self.current_series_info = {'series_uid': series_uid, 'file_paths': file_paths}
                    data_loaded = True

            # Option B: Fallback to directory load
            if not data_loaded and path and os.path.exists(path):
                self.load_dicom_data(path)
                data_loaded = True
            
            if not data_loaded:
                QMessageBox.warning(self, "Load Error", f"Original DICOM data not found.")
                return
            
            # 2. Restore Preset FIRST (before adjustments)
            preset = state.get("preset", "bone")
            self.apply_tissue_preset(preset)

            # 2.5 Restore Color Map
            colormap = state.get("colormap", "gray")
            self.apply_colormap(colormap)
            
            # 3. Restore Measurement Unit
            measurement_unit = state.get("measurement_unit", "mm")
            unit_index = 0 if measurement_unit == 'mm' else 1
            self.unit_combo.setCurrentIndex(unit_index)
            
            # 4. Restore Adjustments
            adjustments = state.get("adjustments", {})
            for key, value in adjustments.items():
                if key in self.adjustment_sliders:
                    self.adjustment_sliders[key].blockSignals(True)
                    self.adjustment_sliders[key].setValue(value)
                    self.adjustment_sliders[key].blockSignals(False)
                    self.on_adjustment_changed(key, value)
            
            # 5. Restore Viewports (Camera, Window/Level, Slices)
            vp_states = state.get("viewports", {})
            for name, vp_state in vp_states.items():
                if name in self.viewports:
                    vp = self.viewports[name]
                    
                    # Restore Slice (for 2D)
                    if "current_slice" in vp_state and name != '3d':
                        vp.current_slice = vp_state["current_slice"]
                        vp._update_slice_position()
                        if vp.reslice: 
                            vp.reslice.Update()
                        vp._update_slice_text()
                    
                    # Restore Window/Level for 2D views
                    if name != '3d' and vp.image_slice:
                        if "window" in vp_state and "level" in vp_state:
                            prop = vp.image_slice.GetProperty()
                            prop.SetColorWindow(vp_state["window"])
                            prop.SetColorLevel(vp_state["level"])
                    
                    # Restore Camera
                    cam_data = vp_state.get("camera", {})
                    cam = vp.renderer.GetActiveCamera()
                    
                    if name == '3d':
                        # Reset camera first for 3D
                        cam.SetPosition(0, 0, 1)
                        cam.SetFocalPoint(0, 0, 0)
                        cam.SetViewUp(0, 1, 0)
                        
                        if "focal_point" in cam_data:
                            cam.SetFocalPoint(cam_data["focal_point"])
                        if "position" in cam_data:
                            cam.SetPosition(cam_data["position"])
                        if "view_up" in cam_data:
                            cam.SetViewUp(cam_data["view_up"])
                        if "view_angle" in cam_data:
                            cam.SetViewAngle(cam_data["view_angle"])
                        
                        # Restore projection type
                        parallel = cam_data.get("parallel_projection", False)
                        cam.SetParallelProjection(parallel)
                        if parallel and "parallel_scale" in cam_data:
                            cam.SetParallelScale(cam_data["parallel_scale"])
                        
                        # Update projection menu/toolbar
                        self.perspective_action.setChecked(not parallel)
                        self.parallel_action.setChecked(parallel)
                        self.proj_toggle_btn.setChecked(parallel)
                        self.proj_toggle_btn.setText("📷 Ortho" if parallel else "📷 Persp")
                        
                        # Restore 3D-specific visibility settings
                        if "bounding_box_visible" in vp_state:
                            vp.set_bounding_box_visible(vp_state["bounding_box_visible"])
                            self.bounding_box_action.setChecked(vp_state["bounding_box_visible"])
                        if "bbox_labels_visible" in vp_state:
                            vp.set_bbox_labels_visible(vp_state["bbox_labels_visible"])
                        if "scale_rulers_visible" in vp_state:
                            vp.set_scale_rulers_visible(vp_state["scale_rulers_visible"])
                    else:
                        # 2D views
                        if "position" in cam_data: 
                            cam.SetPosition(cam_data["position"])
                        if "focal_point" in cam_data: 
                            cam.SetFocalPoint(cam_data["focal_point"])
                        if "view_up" in cam_data: 
                            cam.SetViewUp(cam_data["view_up"])
                        if "parallel_scale" in cam_data: 
                            cam.SetParallelScale(cam_data["parallel_scale"])
                    
                    vp.renderer.ResetCameraClippingRange()
                    vp.render()
            
            # 6. Restore Clipping Plane State
            clipping_data = state.get("clipping", {})
            if clipping_data and '3d' in self.viewports:
                vp_3d = self.viewports['3d']
                
                # Restore orientation first (before enabling)
                orient_index = clipping_data.get("orientation_index", 0)
                self.clipping_orient_combo.blockSignals(True)
                self.clipping_orient_combo.setCurrentIndex(orient_index)
                self.clipping_orient_combo.blockSignals(False)
                
                # Restore plane position if saved
                if "origin" in clipping_data and "normal" in clipping_data:
                    if vp_3d.clipping_plane_widget:
                        try:
                            rep = vp_3d.clipping_plane_widget.GetRepresentation()
                            rep.SetOrigin(clipping_data["origin"])
                            rep.SetNormal(clipping_data["normal"])
                        except Exception as e:
                            print(f"Warning: Could not restore clipping plane position: {e}")
                
                # Restore enabled state (this will apply the clipping)
                enabled = clipping_data.get("enabled", False)
                self.clipping_checkbox.blockSignals(True)
                self.clipping_checkbox.setChecked(enabled)
                self.clipping_checkbox.blockSignals(False)
                self.clipping_action.setChecked(enabled)
                vp_3d.set_clipping_enabled(enabled)
            
            # 7. Restore Measurements AFTER viewports are rendered
            QApplication.processEvents()
            
            for name, vp_state in vp_states.items():
                if name in self.viewports:
                    vp = self.viewports[name]
                    measurements = vp_state.get("measurements", [])
                    if measurements:
                        vp.restore_measurements(measurements)
            
            # Force render all viewports after measurements are restored
            QApplication.processEvents()
            for vp in self.viewports.values():
                vp.render()
            
            # 8. Restore Crosshair
            crosshair_data = state.get("crosshair", {})
            self.crosshair_checkbox.setChecked(crosshair_data.get("enabled", False))
            center = crosshair_data.get("center")
            if center and len(center) == 3:
                self.crosshair_manager.set_position_xyz(center[0], center[1], center[2])
            
            # 9. Restore UI State
            ui_state = state.get("ui_state", {})
            if "bbox_labels_checked" in ui_state:
                self.bbox_labels_checkbox.blockSignals(True)
                self.bbox_labels_checkbox.setChecked(ui_state["bbox_labels_checked"])
                self.bbox_labels_checkbox.blockSignals(False)
                if hasattr(self, 'bbox_labels_action'):
                    self.bbox_labels_action.setChecked(ui_state["bbox_labels_checked"])
            
            if "ruler_enabled" in ui_state:
                self.ruler_checkbox.blockSignals(True)
                self.ruler_checkbox.setChecked(ui_state["ruler_enabled"])
                self.ruler_checkbox.blockSignals(False)
                if hasattr(self, 'ruler_action'):
                    self.ruler_action.setChecked(ui_state["ruler_enabled"])
                # Apply ruler state to viewports
                for vp in self.viewports.values():
                    vp.set_measurement_enabled(ui_state["ruler_enabled"])
            
            if "scale_rulers_action_checked" in ui_state:
                if hasattr(self, 'scale_rulers_action'):
                    self.scale_rulers_action.setChecked(ui_state["scale_rulers_action_checked"])
                if '3d' in self.viewports:
                    self.viewports['3d'].set_scale_rulers_visible(ui_state["scale_rulers_action_checked"])
            
            # 10. Update slice sliders UI to match restored slice positions
            self._update_slice_sliders()
            
            # 11. Update measurement count
            self._update_measurement_count()
            
            self.statusBar().showMessage(f"Work loaded from {file_path}", 3000)
            
        except Exception as e:
            print(f"Load error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Load Error", f"Could not load file: {e}")
    
    def closeEvent(self, event):
        """Clean up VTK on close."""
        try:
            # Cancel any running scan
            if hasattr(self, 'study_browser') and self.study_browser.scanner_thread:
                if self.study_browser.scanner_thread.isRunning():
                    self.study_browser.scanner_thread.cancel()
                    self.study_browser.scanner_thread.wait(1000)
            
            # Finalize viewports
            for viewport in self.viewports.values():
                viewport.finalize()
        except Exception as e:
            print(f"Cleanup error: {e}")
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()