from gcode import Command
from const import *
from session import SerialSession
from main import Backend
import commandAdapters as CA
import json
from wrappers import Brush, HolderPosition, PaintPot
from pathlib import Path
import time

ROOT = Path(__file__).parent

config = json.load(open(ROOT / "configs/brushHolderConfig.json"))
POT = PaintPot(0)


def makeHolderPositions(config):
    """
    Create the holder positions from the config.
    """
    holderPositions = []
    for holderData in config:
        brushes = holderData.pop("brushes")
        holderData["brushes"] = []

        tempHolder = HolderPosition(**holderData)
        for idx, brushData in enumerate(brushes):
            brush = Brush(**brushData, holder=tempHolder, paintPot=POT)
            brush.holder = tempHolder
            tempHolder.brushes.append(brush)
        holderPositions.append(tempHolder)
    return holderPositions


holders = makeHolderPositions(config)


SESSION = SerialSession()


def testHolder(holder_num, brush_limit):
    SESSION.write(str(Command(x=0, y=100, z=0, f=8000)))
    time.sleep(1)
    SESSION.write(str(Command(x=0, y=100, z=BRUSH_HOLDER_ENTRY_Z, f=8000)))
    for brush in holders[holder_num].brushes[:brush_limit]:
        pickupCommands = brush.pickup()
        dropCommands = brush.drop()

        for c in pickupCommands:

            _ = input(f"{str(c)}\nOk?")
            if _ == "y":
                c.f = 8000
            else:
                c.f = 500

            SESSION.write(str(c))
            time.sleep(0.5)

        for c in dropCommands:
            _ = input(f"{str(c)}\nOk?")

            if _ == "y":
                c.f = 8000
            else:
                c.f = 500

            SESSION.write(str(c))
            time.sleep(0.5)


def testOffsets():
    commands = [
        Command(x=0, y=100, z=0, f=8000),
        Command(x=0, y=100, z=BRUSH_HOLDER_ENTRY_Z, f=8000),
    ]
    # for holder in holders:
    holder = holders[0]
    commands.append(
        Command(x=holder.x, y=holder.y, z=BRUSH_HOLDER_ENTRY_Z, f=HOLDER_FEED_RATE)
    )
    for command in commands:
        print(str(command))
        _ = input("Ok?")
        SESSION.write(str(command))
        time.sleep(0.5)


for i in range(0, 6):
    testHolder(i, 3)
