# AIScripter — Portable AI VFX Pipeline

AIScripter is a production-ready, high-performance monorepository that integrates advanced AI visual effects models directly into **After Effects (CEP Extension)** and **DaVinci Resolve (PySide6 standalone UI)**. Powered by a local, portable Python engine running completely inside the Windows `AppData/Roaming` directory, it processes layers, sequences, and compositions without relying on cloud services.

---

## 🎥 Video Showcases

### Adobe After Effects Integration (Modules & Panels)
<p align="center">
  <video src="https://github.com/user-attachments/assets/6be161b0-284f-4cdd-938f-790b84ee66b3" width="32%" autoplay loop muted playsinline title="RIFE 4.6 & SSIM Deduplication"></video>
  <video src="https://github.com/user-attachments/assets/affba898-42d5-41e1-869c-4a049063cc09" width="32%" autoplay loop muted playsinline title="Depth Anything V2 Map"></video>
  <video src="https://github.com/user-attachments/assets/f2725847-515d-4ee8-9808-671dcf549751" width="32%" autoplay loop muted playsinline title="BiRefNet Background Removal"></video>
</p>
<p align="center">
  <em>From left to right: 1. RIFE 4.6 & SSIM Deduplication Pipeline, 2. Depth Anything V2 Map Generation, 3. BiRefNet Background Removal (ProRes 4444 + Alpha).</em>
</p>

### Blackmagic Design DaVinci Resolve Workflow
<p align="center">
  <video src="https://github.com/user-attachments/assets/1ae98204-00a2-437e-91be-13eacfaa004a" width="75%" autoplay loop muted playsinline title="DaVinci Resolve Core App Pipeline"></video>
</p>
<p align="center">
  <em>Standalone PySide6 application processing standalone files with full RIFE interpolation and SSIM video deduplication support.</em>
</p>

---

## ⚡ Key Features

* **RIFE 4.6 Frame Interpolation:** Smooths out fast-paced video, high-action clips, or anime cuts by generating high-quality intermediate frames with tensor grid caching.
* **SSIM Video Deduplication:** Intelligently analyzes frames using Structural Similarity Index (SSIM) to clear duplicate frames, automatically remapping time via ExtendScript.
* **Depth Anything V2:** Generates highly accurate, detailed depth maps optimized for 10-bit HEVC/H.265 export pipelines.
* **BiRefNet Background Removal:** High-fidelity background extraction exporting directly into high-quality ProRes 4444 containing alpha channels, optimized for artistic and toon content.

---

## 📁 Repository Structure

```text
AIScripter/
├── ScripterAE/            # After Effects CEP Extension (HTML/CSS/JS/JSX)
│   ├── main.js            # Main frontend script orchestration
│   └── ...
├── ScripterResolve/       # DaVinci Resolve Integration App (PySide6)
│   ├── run.py             # Main PySide6 UI entry point & DLL redirection
│   └── davinci_integration/
├── Backend/               # Pure Python AI Core Logic
│   ├── backend/
│   │   └── main.py        # Central CLI controller orchestrator (match-case)
│   ├── src/               # Core AI modules (rife, dedup, depth, segment)
│   └── weights/           # Local weights structure (RIFE 4.6 packed out of the box)
├── install.bat            # Dynamic components installer script
└── README.md

```
---

## 💻 System Requirements

* **OS:** Windows 10 / 11 (64-bit)
* **Host Applications:**
  * Adobe After Effects (with CEP extensions support)
  * Blackmagic Design DaVinci Resolve
* **Hardware:** NVIDIA GPU with CUDA support recommended for optimal AI processing speeds.

---

## 🔧 Installation & Deployment

The repository uses an automated installation script that dynamically sets up the environment from official distribution networks to keep the initial footprint lightweight.

1. Clone or download this monorepository to your local machine.
2. Run `install.bat` as **Administrator**.
3. Select your deployment strategy from the interactive menu:
   * **Full Pipeline:** Deploys both host interfaces and initializes the core.
   * **After Effects Only:** Installs the Adobe CEP extension panel.
   * **DaVinci Resolve Only:** Sets up the Python PySide6 standalone app wrapper.

The installer automatically downloads an isolated, portable instance of Python embeddable package, deploys `pip`, installs all necessary production-ready libraries (`torch`, `transformers`, `opencv`), pulls optimized static builds of `FFmpeg`/`FFprobe`, and maps everything neatly inside `%APPDATA%\MyScripterAE`.

---

## 🛠️ Tech Stack

* **Frontends:** JavaScript (ES6+), ExtendScript, Python (PySide6 / Qt)
* **AI Engine Backend:** Python 3.13 (Embeddable Edition)
* **Core Libraries:** PyTorch, Transformers, Kornia, OpenCV, Pathlib
* **Media Pipeline:** FFmpeg Shared Architecture (ProRes 4444 Alpha, 10-bit HEVC)
