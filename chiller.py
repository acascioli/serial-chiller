import time
import serial

# Mapping for standard "in" commands.
RESPONSES = {
    "VERSION": "JULABO_V3.0",
    "status": "03 REMOTE START",
    "in_mode_05": "1",
    "in_mode_04": "0",
    "in_sp_06": "14.55",
    "in_sp_00": "2.00",
    "in_pv_00": "14.55",
    "in_pv_02": "---.--",
    "in_pv_01": "-100",
}

def simulate_chiller():
    ser = serial.Serial(
        port="/tmp/ttyV1",  # Adjust for your system (e.g., COMx on Windows)
        baudrate=4800,
        bytesize=serial.SEVENBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
    )
    print("Simulated chiller is running. Waiting for commands...")
    while True:
        # Read command terminated by CR (0x0D)
        data = ser.read_until(b'\r').decode("ascii").strip()
        if data:
            print(f"Simulated Chiller Received: {data}")
            if data.startswith("out_sp_00"):
                parts = data.split(" ", 1)
                if len(parts) > 1:
                    response = f"Setpoint updated to {parts[1]}"
                else:
                    response = "Missing parameter for out_sp_00"
            elif data.startswith("out_mode_05"):
                parts = data.split(" ", 1)
                if len(parts) > 1:
                    response = "Chiller turned on" if parts[1] == "1" else "Chiller turned off"
                else:
                    response = "Missing parameter for out_mode_05"
            else:
                response = RESPONSES.get(data, "OK")
            full_response = response + "\r\n"
            time.sleep(0.05)
            ser.write(full_response.encode("ascii"))
            print(f"Simulated Chiller Sent: {response}")
        else:
            time.sleep(0.05)

if __name__ == "__main__":
    simulate_chiller()
