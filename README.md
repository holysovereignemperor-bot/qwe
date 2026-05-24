# OmniAgent OS: Ultimate Multi-Agent Computer Use Ecosystem

OmniAgent OS is a production-ready, ultra-optimized autonomous agent framework designed specifically for macOS (M1/M2/M3). It matches and exceeds the capabilities of state-of-the-art computer-use systems by combining native OS accessibility integration with advanced multi-agent orchestration.

## Key Features
- **Multi-Agent Architecture**:
  - **Architect**: High-level planning and DAG generation.
  - **Executor**: Vision-Language-Action (VLA) execution with self-repair.
  - **Auditor**: Reflective verification and causal analysis.
- **Native macOS Perception**: Uses `PyObjC` to parse the `AXUIElement` tree (Accessibility Hierarchy) for 0% idle CPU overhead.
- **Neural Memory Vault**: SQLite-based long-term memory that learns from successful task patterns.
- **Cyber-Minimalist GUI**: A premium `customtkinter` interface with resource monitoring and ghost overlays.
- **Security Guardrails**: Hardened terminal command blacklist and directory traversal protection.
- **Remote Control**: FastAPI-based dashboard with an emergency kill switch.
- **Optimized for M1**: Aggressive memory management (GC flushing, JPEG compression) to strictly respect the 8GB RAM ceiling.

## Installation
Run the one-click bootstrap script:
```bash
chmod +x setup.sh
./setup.sh
```

## Usage
Launch the application:
```bash
python3 main.py
```
Or use CLI mode:
```bash
python3 main.py --cli --goal "Research top competitors and save to a file"
```

## Requirements
- macOS (Apple Silicon recommended)
- Python 3.10+
- Accessibility Permissions granted to your Terminal/IDE.

## License
MIT
