# DICOM Medical Imaging Visualizer

A desktop 3D medical imaging application built with Python, VTK, and PyQt5. Developed as a Scientific Data Visualisation project at Universiti Malaysia Sabah (UMS).

Supports loading DICOM image series and visualising them as GPU-accelerated 3D volumes with synchronised Multi-Planar Reconstruction (MPR) across axial, sagittal, and coronal planes — alongside interactive diagnostic tools for anatomical analysis.

---

## Features

### Visualisation
- **GPU-accelerated 3D volume rendering** via VTK with real-time interaction
- **Synchronised MPR** — axial, sagittal, and coronal 2D slice views linked to the 3D viewport
- **Transfer functions** — tissue segmentation presets for bone, soft tissue, and X-ray appearance
- **Perspective and orthographic projection** modes for the 3D viewport
- **Window / Level adjustment** sliders for contrast control on 2D slices

### Data Loading
- **Smart Scan** — recursive DICOM directory scanner using `pydicom`; auto-discovers all series within a folder and presents them as selectable study cards
- Supports multi-series studies (Brain, Spine, Knee, Pelvis, etc.)
- Graceful fallback if `pydicom` is not installed

### Interaction & Diagnostics
- **Euclidean distance measurement tool** — click-to-place rulers with mm readout across any viewport
- **Interactive 3D clipping plane** — widget-controlled plane to reveal internal anatomy
- **Crosshair synchronisation** — clicking in any 2D view updates the position indicator across all viewports
- **Bounding box and scale rulers** in the 3D viewport
- **Camera settings dialog** — configure FOV, parallel scale, near/far clipping planes per viewport

### Session Management
- **Save / Load workspace** — full application state serialised to JSON, including camera positions, slice indices, window/level values, measurements, clipping plane state, and transfer function settings
- Enables reproducible multi-session analysis without re-importing data

### UI
- Dark theme with teal (`#00bcd4`) accent — built with PyQt5 stylesheets
- Animated video splash screen on launch (`splash.py`)
- Dockable control panels for transfer functions, slicing, and measurements

---

## Tech Stack

| Layer | Technology |
|---|---|
| Visualisation | VTK 9.x |
| GUI Framework | PyQt5 |
| DICOM Parsing | pydicom |
| Numerical | NumPy |
| Language | Python 3.8+ |

---

## Screenshots

<img width="1280" height="680" alt="image" src="https://github.com/user-attachments/assets/e6f0d77e-8311-4906-93e2-108027b218f2" />
<img width="1280" height="680" alt="image" src="https://github.com/user-attachments/assets/96bdc764-2e81-4756-a162-5d38e42e37dd" />
<img width="1280" height="680" alt="image" src="https://github.com/user-attachments/assets/361da485-446c-4845-a300-bd755fea0e73" />
<img width="1280" height="680" alt="image" src="https://github.com/user-attachments/assets/c1171d7b-33b5-45ad-b880-6555573c84a4" />

---

## Installation

### Prerequisites

- Python 3.8 or higher
- A system with OpenGL support (required by VTK)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/nrsakinh/dicom-medical-visualizer.git
cd dicom-medical-visualizer

# 2. Create and activate a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Run

```bash
# Launch with splash screen
python splash.py

# Launch directly (no splash)
python main.py
```

---

## Usage

### Loading DICOM Data

1. Launch the application
2. Click **Open DICOM Folder** in the toolbar or `File > Open`
3. Select the root folder containing your DICOM series
4. The Smart Scan will auto-detect all series — select one from the study browser panel
5. The volume will load into all four viewports

### Navigating Viewports

| Action | How |
|---|---|
| Rotate 3D view | Left-click drag |
| Pan | Middle-click drag |
| Zoom | Scroll wheel |
| Scroll slices (2D) | Scroll wheel in axial/sagittal/coronal view |
| Window / Level | Right-click drag in 2D view |

### Measurements

1. Enable the ruler tool from the toolbar
2. Click two points in any viewport
3. Distance displayed in millimetres

### Clipping Plane

1. Tick **Clipping Plane** in the control panel
2. Drag the interactive plane widget in the 3D viewport
3. Change orientation (Axial / Sagittal / Coronal) via the dropdown

### Saving a Session

`File > Save Session` — saves a `.json` file capturing the full state of your current workspace. Reload it later via `File > Load Session`.

> **Note:** Session files store absolute file paths. If you move your DICOM data, update the paths in the JSON manually.

---

## DICOM Test Datasets

DICOM data is not included in this repository due to file size. The following free public datasets are compatible:

| Dataset | Source |
|---|---|
| Visible Human Project (Male/Female) | [nlm.nih.gov](https://www.nlm.nih.gov/research/visible/visible_human.html) |
| CT scans — various anatomy | [The Cancer Imaging Archive (TCIA)](https://www.cancerimagingarchive.net/) |
| Sample DICOM files | [Rubo Medical — OsiriX sample datasets](https://www.osirix-viewer.com/resources/dicom-image-library/) |

Download and point the application at the extracted folder.

---

## Project Structure

```
dicom-medical-visualizer/
├── main.py              # Main application window and all VTK logic
├── splash.py            # Animated video splash screen
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Academic Context

Developed as **Assignment 2** for the Scientific Data Visualisation module (SV40303) at Universiti Malaysia Sabah, Faculty of Science and Technology.

**Programme:** BSc (Hons.) Mathematics Computer Graphics  
**Student:** Nur Sakinah Binti Mohammad Ali  
**Supervisor context:** Scientific Data Visualisation, UMS

---

## Known Limitations

- Session JSON files store absolute file paths — not portable across machines without manual editing
- Splash screen video requires a codec-compatible Qt multimedia backend; falls back gracefully if unsupported
- Very large DICOM series (1000+ slices) may have slower initial load times depending on available RAM

---

## License

This project was developed for academic purposes. If reusing or adapting the code, please credit the original author.
