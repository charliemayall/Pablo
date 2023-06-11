from gcode import Command
from const import *
from session import SerialSession
from main import Backend
import commandAdapters as CA
import json
from wrappers import Brush, HolderPosition, PaintPot
from pathlib import Path
import time
import numpy as np
from PIL import Image
import math

ROOT = Path(__file__).parent
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
            brush = Brush(**brushData, paintPot=POT, holder=tempHolder)
            brush.holder = tempHolder
            tempHolder.brushes.append(brush)
        holderPositions.append(tempHolder)
    return holderPositions


def strokeOfLength(length, numPoints=100):
    midX = (BED_MAX_X - BED_MIN_X) / 2
    midY = (BED_MAX_Y - BED_MIN_Y) / 2
    xVals = np.linspace(midX - length // 2, midX + length // 2, num=numPoints)

    return [
        Command(x=x, y=midY, z=BRUSH_TIP_Z_OFFSET, f=8000, flags=["contact"])
        for x in xVals
    ]


def testSquare():
    centerX = (BED_MAX_X - BED_MIN_X) / 2
    centerY = (BED_MAX_Y - BED_MIN_Y) / 2
    squareCoords = [
        (centerX - 50, centerY + 50),
        (centerX + 50, centerY + 50),
        (centerX + 50, centerY - 50),
        (centerX - 50, centerY - 50),
        (centerX - 50, centerY + 50),
    ]
    commands = []
    for idx, coords in enumerate(squareCoords):
        if idx == len(squareCoords) - 1:
            commands.append(
                Command(x=coords[0], y=coords[1], z=BRUSH_TIP_Z_OFFSET, f=8000)
            )
            commands.append(
                Command(x=coords[0], y=coords[1], z=BRUSH_HOLDER_ENTRY_Z, f=8000)
            )

        else:
            xPaddedValues = np.linspace(coords[0], squareCoords[idx + 1][0], num=50)
            yPaddedValues = np.linspace(coords[1], squareCoords[idx + 1][1], num=50)
            for x, y in zip(xPaddedValues, yPaddedValues):
                commands.append(Command(x=x, y=y, z=BRUSH_TIP_Z_OFFSET, f=8000))

    return commands


def testWave():
    centerX = (BED_MAX_X - BED_MIN_X) / 2
    centerY = (BED_MAX_Y - BED_MIN_Y) / 2
    commands = []
    sineWave = np.sin(np.linspace(0, 2 * math.pi, num=100))
    xStart = centerX - 50
    xEnd = centerX + 50
    yStart = centerY
    xCoords = np.linspace(xStart, xEnd, num=100)
    yCoords = (sineWave * 50) + yStart
    for x, y in zip(xCoords, yCoords):
        commands.append(Command(x=x, y=y, z=BRUSH_TIP_Z_OFFSET, f=8000))
    return commands


def testCircle():
    centerX = (BED_MAX_X - BED_MIN_X) / 2
    centerY = (BED_MAX_Y - BED_MIN_Y) / 2
    a = 2
    b = 3
    r = 50

    # The lower this value the higher quality the circle is with more points generated
    stepSize = 0.1

    # Generated vertices
    positions = []

    t = 0
    while t < 2 * math.pi:
        positions.append((r * math.cos(t) + a, r * math.sin(t) + b))
        t += stepSize
    commands = []
    for idx, pos in enumerate(positions):
        if idx == len(positions) - 1:
            commands.append(
                Command(
                    x=centerX + pos[0],
                    y=centerY + pos[1],
                    z=BRUSH_HOLDER_ENTRY_Z,
                    f=8000,
                )
            )
            commands.append(
                Command(
                    x=centerX + pos[0], y=centerY + pos[1], z=BRUSH_TIP_Z_OFFSET, f=8000
                )
            )
        else:
            commands.append(
                Command(
                    x=centerX + pos[0], y=centerY + pos[1], z=BRUSH_TIP_Z_OFFSET, f=8000
                )
            )
    return commands


def leadIn(commands, steps):
    xVals = [c.x for c in commands[:steps]]
    yVals = [c.y for c in commands[:steps]]
    equation = np.polyfit(xVals, yVals, 2)
    equation = np.poly1d(equation)

    startX = commands[0].x
    leadIn = []
    isFirst = True
    z = BRUSH_TIP_Z_OFFSET
    for x in np.linspace(startX, startX + steps, num=steps):
        if isFirst:
            z = BRUSH_HOLDER_ENTRY_Z
            isFirst = False
        leadIn.append(Command(x=x, y=equation(x), z=z, f=8000))
    return leadIn + commands


def testPaintRunOut(brush: Brush):
    commandChunks = []
    commandChunks.append(brush.refill())
    midX = (BED_MAX_X - BED_MIN_X) / 2
    squareBoundsX = (midX - 100, midX + 100)
    squareBoundsY = (POT_BOARD_CORNER_Y + 200, POT_BOARD_CORNER_Y + 400)

    yCoords = [i for i in range(squareBoundsY[0], squareBoundsY[1], 15)]
    xCoords = np.linspace(squareBoundsX[0], squareBoundsX[1], num=200)
    distTravelled = 0
    for y in yCoords:
        commands = []
        for x in xCoords:
            command = Command(x=x, y=y + 200, z=BRUSH_TIP_Z_OFFSET - 4, f=8000)
            if len(commands) > 1:
                distTravelled += commands[-1].distanceTo(command)
            if distTravelled > 50:
                command.y += 5
                distTravelled = 0
            commands.append(command)

        commands.append(Command(z=-1, f=8000))
        commandChunks.append(commands)
    return commandChunks


config = json.load(open(ROOT / "configs/brushHolderConfig.json"))
holder = makeHolderPositions(config)[0]
SESSION = SerialSession()
for chunk in testPaintRunOut(holder.brushes[1]):
    _ = input("another?")
    SESSION.safeWrite(chunk)
