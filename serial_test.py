import serial
import time

# =============================
# CONFIG
# =============================
SERIAL_PORT = "COM3"      # Change to your Arduino port
BAUD_RATE = 115200
TIMEOUT = 1

# =============================
# SERIAL SEND FUNCTION
# =============================
def send_command(ser, command):
    """
    Sends a single command over serial.
    Automatically appends newline.
    """
    message = f"{command}\n"
    ser.write(message.encode("utf-8"))
    print(f"> Sent: {command}")

# =============================
# MAIN
# =============================
def main():
    # Open serial connection
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    time.sleep(2)  # Allow Arduino to reset

    print("Serial tester ready")
    print("Commands:")
    print("  X,Y  -> move servos (e.g. 90,45)")
    print("  1    -> relay ON")
    print("  0    -> relay OFF")
    print("  q    -> quit")

    while True:
        user_input = input("> ").strip()

        if user_input.lower() == "q":
            break

        # Basic validation
        if user_input == "0" or user_input == "1":
            send_command(ser, user_input)

        elif "," in user_input:
            parts = user_input.split(",")
            if len(parts) == 2:
                try:
                    int(parts[0])
                    int(parts[1])
                    send_command(ser, user_input)
                except ValueError:
                    print("Invalid servo values")
            else:
                print("Invalid format (use X,Y)")
        else:
            print("Unknown command")

    ser.close()
    print("Serial closed")

if __name__ == "__main__":
    main()
