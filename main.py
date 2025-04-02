import sys
import time
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QGroupBox,
    QTabWidget, QCheckBox, QComboBox, QLineEdit, QFormLayout
)
from PySide6.QtCore import QObject, QThread, Signal, Qt

# Worker class: accepts a list of (command, parameter) tuples,
# an optional inter_byte_timeout, a flag to append newline,
# a per-byte transmission delay, and a command delay between commands,
# plus port configuration parameters.
class SerialWorker(QObject):
    update_signal = Signal(str)
    finished = Signal()

    def __init__(self, port, commands, baudrate=4800, bytesize=serial.SEVENBITS,
                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=1,
                 inter_byte_timeout=None, append_newline=False, tx_delay=0, command_delay=0.06):
        super().__init__()
        self.port = port
        self.commands = commands  # list of tuples: (command, parameter)
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        self.inter_byte_timeout = inter_byte_timeout
        self.append_newline = append_newline
        self.tx_delay = tx_delay
        self.command_delay = command_delay
        self._is_running = True

    def run(self):
        try:
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                inter_byte_timeout=self.inter_byte_timeout
            )
            for cmd, param in self.commands:
                if not self._is_running:
                    break
                if param is not None and param != "":
                    base_command = f"{cmd} {param}"
                else:
                    base_command = f"{cmd}"
                if self.append_newline:
                    full_command = f"{base_command}\r\n"
                else:
                    full_command = f"{base_command}\r"
                self.update_signal.emit(f"Sending: {full_command.strip()}")
                if self.tx_delay > 0:
                    for ch in full_command:
                        ser.write(ch.encode("ascii"))
                        ser.flush()
                        time.sleep(self.tx_delay)
                else:
                    ser.write(full_command.encode("ascii"))
                    ser.flush()
                time.sleep(self.command_delay)
                raw_response = ser.readline()
                if not raw_response:
                    response = "No response"
                else:
                    response = raw_response.decode("ascii", errors="ignore").rstrip("\r\n")
                self.update_signal.emit(f"Received: {response}\n")
            ser.close()
        except Exception as e:
            self.update_signal.emit(f"Error: {e}")
        self.finished.emit()

    def stop(self):
        self._is_running = False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Julabo Chiller Communication Interface")
        self.resize(600, 800)
        main_layout = QVBoxLayout(self)

        # --- Serial Port Selection ---
        port_layout = QHBoxLayout()
        port_label = QLabel("Serial Port:")
        self.port_combo = QComboBox()
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.refresh_ports_button.clicked.connect(self.populate_ports)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        port_layout.addWidget(self.refresh_ports_button)
        main_layout.addLayout(port_layout)

        # Option to bypass dropdown.
        manual_layout = QHBoxLayout()
        self.manual_checkbox = QCheckBox("Use manual port entry")
        self.manual_checkbox.stateChanged.connect(self.toggle_manual_entry)
        self.manual_port_edit = QLineEdit()
        self.manual_port_edit.setPlaceholderText("Enter port (e.g., COM11 or /dev/ttyXYZ)")
        self.manual_port_edit.setEnabled(False)
        manual_layout.addWidget(self.manual_checkbox)
        manual_layout.addWidget(self.manual_port_edit)
        main_layout.addLayout(manual_layout)

        # Port info label.
        self.port_info_label = QLabel("Select a port to see details.")
        main_layout.addWidget(self.port_info_label)
        self.populate_ports()
        self.port_combo.currentIndexChanged.connect(self.show_port_info)

        # --- Port Settings Tab ---
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        self.create_port_settings_tab()
        self.tab_widget.addTab(self.port_settings_tab, "Port Settings")

        # --- Commands Tab ---
        self.create_commands_tab()
        self.tab_widget.addTab(self.commands_tab, "Commands")

        # --- Custom Commands Tab ---
        self.create_custom_tab()
        self.tab_widget.addTab(self.custom_tab, "Custom Commands")

        # --- Additional Options ---
        timeout_layout = QHBoxLayout()
        self.inter_byte_timeout_checkbox = QCheckBox("Enable inter-byte timeout")
        self.inter_byte_timeout_checkbox.stateChanged.connect(self.toggle_inter_byte_timeout)
        self.inter_byte_timeout_edit = QLineEdit()
        self.inter_byte_timeout_edit.setPlaceholderText("Timeout in seconds (e.g., 0.05)")
        self.inter_byte_timeout_edit.setEnabled(False)
        timeout_layout.addWidget(self.inter_byte_timeout_checkbox)
        timeout_layout.addWidget(self.inter_byte_timeout_edit)
        main_layout.addLayout(timeout_layout)

        newline_layout = QHBoxLayout()
        self.append_newline_checkbox = QCheckBox("Append newline (\\n) after carriage return")
        newline_layout.addWidget(self.append_newline_checkbox)
        main_layout.addLayout(newline_layout)

        tx_delay_layout = QHBoxLayout()
        self.tx_delay_checkbox = QCheckBox("Enable transmission byte delay")
        self.tx_delay_checkbox.stateChanged.connect(self.toggle_tx_delay)
        self.tx_delay_edit = QLineEdit()
        self.tx_delay_edit.setPlaceholderText("Delay in seconds per byte (e.g., 0.01)")
        self.tx_delay_edit.setEnabled(False)
        tx_delay_layout.addWidget(self.tx_delay_checkbox)
        tx_delay_layout.addWidget(self.tx_delay_edit)
        main_layout.addLayout(tx_delay_layout)

        command_delay_layout = QHBoxLayout()
        self.command_delay_checkbox = QCheckBox("Enable command delay between commands")
        self.command_delay_checkbox.stateChanged.connect(self.toggle_command_delay)
        self.command_delay_edit = QLineEdit()
        self.command_delay_edit.setPlaceholderText("Delay in seconds (default 0.06)")
        self.command_delay_edit.setText("0.06")
        self.command_delay_edit.setEnabled(False)
        command_delay_layout.addWidget(self.command_delay_checkbox)
        command_delay_layout.addWidget(self.command_delay_edit)
        main_layout.addLayout(command_delay_layout)

        # --- Bottom Buttons ---
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Communication")
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self.clear_log)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.clear_log_button)
        main_layout.addLayout(button_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        self.start_button.clicked.connect(self.start_communication)
        self.thread = None
        self.worker = None

        self.custom_command_counter = 0

    def create_port_settings_tab(self):
        self.port_settings_tab = QWidget()
        layout = QFormLayout()
        self.baudrate_edit = QLineEdit("4800")
        layout.addRow("Baudrate:", self.baudrate_edit)
        self.bytesize_combo = QComboBox()
        self.bytesize_combo.addItem("7")
        self.bytesize_combo.addItem("8")
        self.bytesize_combo.setCurrentText("7")
        layout.addRow("Bytesize:", self.bytesize_combo)
        self.parity_combo = QComboBox()
        self.parity_combo.addItem("N")
        self.parity_combo.addItem("E")
        self.parity_combo.addItem("O")
        self.parity_combo.setCurrentText("N")
        layout.addRow("Parity:", self.parity_combo)
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItem("1")
        self.stopbits_combo.addItem("2")
        self.stopbits_combo.setCurrentText("2")
        layout.addRow("Stopbits:", self.stopbits_combo)
        self.timeout_edit = QLineEdit("1")
        layout.addRow("Timeout (sec):", self.timeout_edit)
        self.port_settings_tab.setLayout(layout)

    def create_commands_tab(self):
        self.commands_tab = QWidget()
        layout = QVBoxLayout(self.commands_tab)
        commands_group = QGroupBox("Commands (Select & Order, Drag to reorder)")
        group_layout = QVBoxLayout()
        self.command_list = QListWidget()
        self.command_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.standard_commands = [
            "VERSION", "status", "in_mode_05", "in_mode_04",
            "in_sp_06", "in_sp_00", "in_pv_00", "in_pv_02",
            "in_pv_01", "out_sp_00", "out_mode_05"
        ]
        for cmd in self.standard_commands:
            item = QListWidgetItem(cmd)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked)
            self.command_list.addItem(item)
        group_layout.addWidget(self.command_list)
        select_buttons_layout = QHBoxLayout()
        self.select_all_button = QPushButton("Select All")
        self.deselect_all_button = QPushButton("Deselect All")
        self.select_all_button.clicked.connect(self.select_all)
        self.deselect_all_button.clicked.connect(self.deselect_all)
        select_buttons_layout.addWidget(self.select_all_button)
        select_buttons_layout.addWidget(self.deselect_all_button)
        group_layout.addLayout(select_buttons_layout)
        commands_group.setLayout(group_layout)
        layout.addWidget(commands_group)
        self.out_params_group = QGroupBox("Out Command Parameters")
        self.out_params_layout = QVBoxLayout()
        self.out_params_widgets = {}
        for cmd in ["out_sp_00", "out_mode_05"]:
            hlayout = QHBoxLayout()
            label = QLabel(cmd)
            line_edit = QLineEdit()
            if cmd == "out_sp_00":
                line_edit.setText("24.00")
            elif cmd == "out_mode_05":
                line_edit.setText("1")
            hlayout.addWidget(label)
            hlayout.addWidget(line_edit)
            self.out_params_layout.addLayout(hlayout)
            self.out_params_widgets[cmd] = line_edit
        self.out_params_group.setLayout(self.out_params_layout)
        layout.addWidget(self.out_params_group)

    def create_custom_tab(self):
        self.custom_tab = QWidget()
        layout = QVBoxLayout(self.custom_tab)
        custom_form_layout = QHBoxLayout()
        self.custom_command_edit = QLineEdit()
        self.custom_command_edit.setPlaceholderText("Enter custom command")
        self.custom_param_checkbox = QCheckBox("Accepts parameter")
        self.add_custom_button = QPushButton("Add Custom Command")
        self.add_custom_button.clicked.connect(self.add_custom_command)
        custom_form_layout.addWidget(self.custom_command_edit)
        custom_form_layout.addWidget(self.custom_param_checkbox)
        custom_form_layout.addWidget(self.add_custom_button)
        layout.addLayout(custom_form_layout)
        custom_list_group = QGroupBox("Custom Commands")
        custom_list_layout = QVBoxLayout()
        self.custom_list_display = QListWidget()
        self.custom_list_display.setSelectionMode(QListWidget.ExtendedSelection)
        custom_list_layout.addWidget(self.custom_list_display)
        self.delete_custom_button = QPushButton("Delete Selected Custom Command(s)")
        self.delete_custom_button.clicked.connect(self.delete_selected_custom_commands)
        custom_list_layout.addWidget(self.delete_custom_button)
        custom_list_group.setLayout(custom_list_layout)
        layout.addWidget(custom_list_group)

    def populate_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device, port)
        if self.port_combo.count() == 0:
            self.port_info_label.setText("No serial ports found.")
        else:
            self.show_port_info()

    def show_port_info(self):
        index = self.port_combo.currentIndex()
        port_info = self.port_combo.itemData(index)
        if port_info is None:
            self.port_info_label.setText("No info available.")
        else:
            info_text = (
                f"Device: {port_info.device}\n"
                f"Description: {port_info.description}\n"
                f"HWID: {port_info.hwid}\n"
            )
            if port_info.manufacturer:
                info_text += f"Manufacturer: {port_info.manufacturer}\n"
            if port_info.vid:
                info_text += f"VID: {hex(port_info.vid)}\n"
            if port_info.pid:
                info_text += f"PID: {hex(port_info.pid)}\n"
            self.port_info_label.setText(info_text)

    def toggle_manual_entry(self, _):
        if self.manual_checkbox.isChecked():
            self.manual_port_edit.setEnabled(True)
            self.port_combo.setEnabled(False)
            self.refresh_ports_button.setEnabled(False)
            self.port_info_label.setText("Manual port entry enabled.")
        else:
            self.manual_port_edit.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.refresh_ports_button.setEnabled(True)
            self.show_port_info()

    def toggle_inter_byte_timeout(self, _):
        if self.inter_byte_timeout_checkbox.isChecked():
            self.inter_byte_timeout_edit.setEnabled(True)
        else:
            self.inter_byte_timeout_edit.setEnabled(False)

    def toggle_tx_delay(self, _):
        if self.tx_delay_checkbox.isChecked():
            self.tx_delay_edit.setEnabled(True)
        else:
            self.tx_delay_edit.setEnabled(False)

    def toggle_command_delay(self, _):
        if self.command_delay_checkbox.isChecked():
            self.command_delay_edit.setEnabled(True)
        else:
            self.command_delay_edit.setEnabled(False)

    def select_all(self):
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            item.setCheckState(Qt.Checked)

    def deselect_all(self):
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            item.setCheckState(Qt.Unchecked)

    def add_custom_command(self):
        cmd_text = self.custom_command_edit.text().strip()
        if not cmd_text:
            return
        accepts_param = self.custom_param_checkbox.isChecked()
        self.custom_command_counter += 1
        cmd_id = self.custom_command_counter
        item_unified = QListWidgetItem(cmd_text)
        item_unified.setFlags(item_unified.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_unified.setCheckState(Qt.Checked)
        item_unified.setData(Qt.UserRole, {"custom": True, "accepts_param": accepts_param, "id": cmd_id})
        self.command_list.addItem(item_unified)
        item_custom = QListWidgetItem(cmd_text)
        item_custom.setFlags(item_custom.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item_custom.setCheckState(Qt.Checked)
        item_custom.setData(Qt.UserRole, {"id": cmd_id})
        self.custom_list_display.addItem(item_custom)
        if accepts_param and cmd_text not in self.out_params_widgets:
            hlayout = QHBoxLayout()
            label = QLabel(cmd_text)
            line_edit = QLineEdit()
            hlayout.addWidget(label)
            hlayout.addWidget(line_edit)
            self.out_params_layout.addLayout(hlayout)
            self.out_params_widgets[cmd_text] = line_edit
        self.custom_command_edit.clear()
        self.custom_param_checkbox.setChecked(False)

    def delete_selected_custom_commands(self):
        selected_items = self.custom_list_display.selectedItems()
        for item in selected_items:
            data = item.data(Qt.UserRole)
            if data and "id" in data:
                cmd_id = data["id"]
                row = self.custom_list_display.row(item)
                self.custom_list_display.takeItem(row)
                indices_to_remove = []
                for i in range(self.command_list.count()):
                    unified_item = self.command_list.item(i)
                    udata = unified_item.data(Qt.UserRole)
                    if udata and udata.get("custom") and udata.get("id") == cmd_id:
                        indices_to_remove.append(i)
                for index in reversed(indices_to_remove):
                    removed_item = self.command_list.takeItem(index)
                    cmd_text = removed_item.text()
                    if cmd_text in self.out_params_widgets:
                        del self.out_params_widgets[cmd_text]

    def clear_log(self):
        self.log_text.clear()

    def start_communication(self):
        self.start_button.setEnabled(False)
        commands_to_send = []
        for i in range(self.command_list.count()):
            item = self.command_list.item(i)
            if item.checkState() == Qt.Checked:
                cmd = item.text()
                custom_data = item.data(Qt.UserRole)
                if custom_data is not None:
                    accepts_param = custom_data.get("accepts_param", False)
                    if accepts_param:
                        param_value = self.out_params_widgets.get(cmd).text().strip() if self.out_params_widgets.get(cmd) else ""
                        commands_to_send.append((cmd, param_value))
                    else:
                        commands_to_send.append((cmd, None))
                elif cmd in ["out_sp_00", "out_mode_05"]:
                    param = self.out_params_widgets.get(cmd).text().strip() if self.out_params_widgets.get(cmd) else ""
                    commands_to_send.append((cmd, param))
                else:
                    commands_to_send.append((cmd, None))
        if self.manual_checkbox.isChecked():
            port = self.manual_port_edit.text().strip()
        else:
            port_obj = self.port_combo.currentData()
            if port_obj is None:
                port = ""
            else:
                port = port_obj.device

        if self.inter_byte_timeout_checkbox.isChecked():
            try:
                inter_byte_timeout = float(self.inter_byte_timeout_edit.text().strip())
            except Exception:
                inter_byte_timeout = None
        else:
            inter_byte_timeout = None

        append_newline = self.append_newline_checkbox.isChecked()

        if self.tx_delay_checkbox.isChecked():
            try:
                tx_delay = float(self.tx_delay_edit.text().strip())
            except Exception:
                tx_delay = 0
        else:
            tx_delay = 0

        if self.command_delay_checkbox.isChecked():
            try:
                command_delay = float(self.command_delay_edit.text().strip())
            except Exception:
                command_delay = 0.06
        else:
            command_delay = 0.06

        try:
            baudrate = int(self.baudrate_edit.text().strip())
        except Exception:
            baudrate = 4800
        bytesize_val = self.bytesize_combo.currentText().strip()
        if bytesize_val == "7":
            bytesize = serial.SEVENBITS
        else:
            bytesize = serial.EIGHTBITS
        parity_val = self.parity_combo.currentText().strip().upper()
        if parity_val == "N":
            parity = serial.PARITY_NONE
        elif parity_val == "E":
            parity = serial.PARITY_EVEN
        elif parity_val == "O":
            parity = serial.PARITY_ODD
        else:
            parity = serial.PARITY_NONE
        stopbits_val = self.stopbits_combo.currentText().strip()
        if stopbits_val == "1":
            stopbits = serial.STOPBITS_ONE
        else:
            stopbits = serial.STOPBITS_TWO
        try:
            timeout = float(self.timeout_edit.text().strip())
        except Exception:
            timeout = 1

        self.thread = QThread()
        self.worker = SerialWorker(port, commands_to_send, baudrate=baudrate, bytesize=bytesize,
                                     parity=parity, stopbits=stopbits, timeout=timeout,
                                     inter_byte_timeout=inter_byte_timeout, append_newline=append_newline,
                                     tx_delay=tx_delay, command_delay=command_delay)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.update_signal.connect(self.log_message)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.start_button.setEnabled(True))
        self.thread.start()

    def log_message(self, msg):
        self.log_text.append(msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Julabo Chiller Controller")
    app.setApplicationVersion("1.1.1")
    app.setOrganizationName("Free University of Bolzano")
    app.setOrganizationDomain("unibz.it")
    # Optionally, set the window icon:
    # from PySide6.QtGui import QIcon
    # app.setWindowIcon(QIcon("path/to/your_icon.ico"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
