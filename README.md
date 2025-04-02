# Julabo Chiller Serial Communication Interface

This project provides a graphical interface and simulation tools for communicating with Julabo chillers via RS-232 serial communication.

## 🖥️ Components

### `main.py`

A PySide6-based GUI that allows users to:

- Select serial ports and configure communication parameters (baud rate, stop bits, parity, etc.)
- Send predefined or custom commands to the chiller
- Add per-byte and per-command transmission delays
- View and log chiller responses in real-time

### `chiller.py`

A Python script simulating a Julabo chiller. It listens on a virtual serial port and responds to commands based on predefined mappings. Useful for testing without actual hardware.

### `socat` (Linux/macOS only)

Used to create a pair of linked virtual serial ports for testing (`/tmp/ttyV0` and `/tmp/ttyV1`). For example:

```bash
socat -d -d PTY,link=/tmp/ttyV0,raw,echo=0 PTY,link=/tmp/ttyV1,raw,echo=0
```
