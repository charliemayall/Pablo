from numpy import index_exp
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
SESSION = SerialSession()
POT = PaintPot(0, "00ff00")


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
            brush = Brush(size=0, holder=tempHolder, holderSlotIndex=idx, paintPot=POT)
            brush.holder = tempHolder
            tempHolder.brushes.append(brush)
        holderPositions.append(tempHolder)
    return holderPositions


def testPot(brush: Brush, inp=False):
    commands = brush.refill()
    reversedCommands = brush.refill()
    for command in commands:
        print(repr(command))
        print(command)
        command.f = 6000

        SESSION.safeWrite(command)
    for command in reversedCommands:
        command.f = 4000


holders = makeHolderPositions(config)
holder = holders[0]
brush = holder.brushes[0]
for i in range(0, 2):
    testPot(brush, inp=i != 0)
    _ = input("POT COMPLETE")
