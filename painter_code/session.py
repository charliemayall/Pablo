from pathlib import Path
import serial
import time
from const import *

ROOT = Path(__file__).parent


class SerialSession:
    def __init__(self):
        self.c_line = []
        self.g_count = 0
        self.l_count = 0
        self.ready = False
        self.session = serial.Serial("/dev/ttyACM0", 115200)
        # Wake up grbl
        self.session.write("\r\n\r\n".encode())
        time.sleep(5)

        self.session.flushInput()

        self.home()

    def home(self):
        self._write("$H")

        time.sleep(5)
        res = self._write("$?")

        while not res.startswith("<Idle") or res == "ok":
            res = self.session.readline().decode().strip()
            print(res)
        self.ready = True

    def _write(self, text):
        if not text.endswith("\n"):
            text += "\n"
        self.session.write(text.encode())
        self.session.flushInput()  # Flush startup text in serial input
        grbl_out = (
            self.session.readline()
        )  # Wait for grbl response with carriage return
        output = grbl_out.decode().strip()
        if "ALARM" in output:
            print(text)
        print(output)
        return output

    def safeWrite(self, commands):
        if not isinstance(commands, list):
            commands = [commands]
        if not isinstance(commands[0], str):
            cStrings = [str(c) for c in commands]
        else:
            cStrings = commands

        ok_b = bytes("ok", "utf-8")
        error_b = bytes("error", "utf-8")
        for line in cStrings:
            self.l_count += 1  # Iterate line counter
            l_block = line.strip()
            self.c_line.append(
                len(l_block) + 1
            )  # Track number of characters in grbl serial read buffer
            grbl_out = ""
            while sum(self.c_line) >= MAX_BUFFER_SIZE - 1 | self.session.inWaiting():
                out_temp = self.session.readline().strip()  # Wait for grbl response
                if out_temp.find(ok_b) < 0 and out_temp.find(error_b) < 0:
                    print("  Debug: ", out_temp)  # Debug response
                else:
                    grbl_out += out_temp.decode("utf-8")
                    self.g_count += 1  # Iterate g-code counter
                    grbl_out += str(self.g_count)
                    # Add line finished indicator
                    del self.c_line[
                        0
                    ]  # Delete the block character count corresponding to the last 'ok'

            self.session.write(bytes(l_block + "\n", "utf-8"))  # Print g-code block
        return grbl_out
