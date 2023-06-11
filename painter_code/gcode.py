import math
from const import *
from pathlib import Path

ROOT = Path(__file__).parent


class Command:
    """
    Parameters
    ----------
    x : float
        x coordinate
    y : float
        y coordinate
    z : float
        z coordinate
    f : float
        feed rate
    flags : list | str | None
        flags for identifying the command type
        e.g. "contact", "lift"

    """

    _autoinc = 0

    @classmethod
    def autoincrement(cls):
        cls._autoinc += 1
        return cls._autoinc

    def __init__(self, x=None, y=None, z=None, f=None, flags=None, command=None):
        self.id = Command.autoincrement()
        self.x = x
        self.y = y
        self.z = z
        self.f = f
        self.flags = flags if isinstance(flags, list) else [flags] if flags else []
        self.commandType = "G1" if command is None else command

    def __str__(self):
        coords = self._convCoords()
        x, y, z = coords
        base = f"{self.commandType}"
        if self.x is not None:
            base += f" X{x:.3f}"
        if self.y is not None:
            base += f" Y{y:.3f}"
        if self.z is not None:
            base += f" Z{z:.3f}"
        base += f" F{self.f}"
        return base

    def __repr__(self):
        return f"""Command(id={self.id}, gcode_command={self.commandType}, x={self.x}, y={self.y},
        z={self.z}, feed={self.f}, flags={self.flags})"""

    def distanceTo(self, other: "Command"):
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __eq__(self, other):
        return (
            self.x == other.x
            and self.y == other.y
            and self.z == other.z
            and self.f == other.f
        )

    def _convCoords(self):
        xConv = -1 * self.x if self.x is not None else None
        yConv = -1 * self.y if self.y is not None else None

        return [xConv, yConv, self.z]

    def hasFlag(self, flag):
        return flag in self.flags


class Pause(Command):
    """
    Use to add a pause at a position
    """

    def __init__(self, x, y, z, f):
        super().__init__(x, y, z, f)
        self.pause = True

    def __str__(self):
        return """
        G1 X{self.x} Y{self.y} Z{self.z} F{self.f}
        \nM0; stop and wait for user input
        """

    def __eq__(self, other):
        return self.pause == other.pause


class GcodeMaker:
    """
    Takes stream data in the form 207.516 311.226 0.11 344.786
    Data should be the coordinates for a single stroke
    Generates a list of commands:Command
    """

    def __init__(self):
        self.commands: list[Command] = []

    def parse(self, streamData):
        """
        streamData is a list of strings in the form "207.516 311.226 0.11 344.786"
        """
        commands = []
        for line in streamData:
            if line == "":
                continue
            data = line.split(" ")
            x = float(data[0])
            y = float(data[1])
            z = self.parsePressure(data[2])
            f = min([int(float(data[3]) * 60), MAX_FEED_RATE])
            commands.append(Command(x, y, z, f, flags=["contact"]))

        self.commands = commands
        return str(self)

    def parsePressure(self, pressure):
        """
        Alters the value of the z axis based on the pressure
        Needs to be adjusted while we test
        """
        pressure = float(pressure)
        return max(BRUSH_TIP_Z_OFFSET - pressure * 1, BED_MIN_Z)

    def addCommand(self, command: Command):
        self.commands.append(command)

    def dump(self, filename: str = None):
        """
        Returns a string of gcode, or writes to a file
        Command list is cleared after dump
        """
        if filename is None:
            return self.clear()
        with open(filename, "w") as f:
            for command in self.commands:
                f.write(self.clear() + "\n")

    def clear(self):
        ret = str(self)

        self.commands = []
        return ret

    def __str__(self):
        return "\n".join([str(command) for command in self.commands])
