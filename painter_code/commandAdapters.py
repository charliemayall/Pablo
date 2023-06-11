from gcode import Command
from const import *
import numpy as np



def startAndEndLift(commands):
    new = []
    start = commands[0]
    new.append(Command(z=0, f=BASE_FEED_RATE, flags=["adapter", "lift"]))
    new.append(Command(x=start.x, y=start.y, z=0, f=BASE_FEED_RATE, flags=["contact"]))
    new.extend(commands)

    new.append(Command(z=0, f=BASE_FEED_RATE, flags=["adapter", "lift"]))
    return new


def speedUp(commands):
    new = []
    for command in commands:
        command.f = 8000
        command.x = round(command.x, 2)
        command.y = round(command.y, 2)

        new.append(command)
    return new


def mirrorOnY(commands):

    new = []
    for command in commands:
        if not command.hasFlag("contact"):
            new.append(command)
            continue
        y = command.y
        if y is None:
            new.append(command)
            continue
        y = abs(BED_MIN_Y + y)
        c = Command(
            x=command.x,
            y=y,
            z=command.z,
            f=command.f,
            flags=command.flags + ["mirrorOnY", "adapter"],
        )
        new.append(c)
    return new


def checkLimits(commands):
    coords = [c._convCoords() for c in commands]
    x, y, z = zip(*coords)
    x = [x for x in x if x is not None]
    y = [y for y in y if y is not None]
    z = [z for z in z if z is not None]
    x_min = min(x)
    x_max = max(x)
    y_min = min(y)
    y_max = max(y)
    z_min = min(z)
    z_max = max(z)

    if any(
        [
            x_min < BED_MIN_X,
            x_max > BED_MAX_X,
            y_min < BED_MIN_Y,
            y_max > BED_MAX_Y,
            z_min < BED_MIN_Z,
            z_max > BED_MAX_Z,
        ]
    ):
        with open("error.txt", "w") as f:
            f.write(str(commands))
        raise Exception("Command outside of bed limits")
    return commands


def leadIn(commands, steps=20):
    if len(commands) < steps * 2:
        steps = len(commands) // 10
    if any([c.hasFlag("pointillism") for c in commands]):
        raise Exception("Lead in not supported for pointillism")
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
        leadIn.append(
            Command(x=x, y=equation(x), z=z, f=8000, flags=["adapter", "leadIn"])
        )
    return leadIn + commands


class Styles:
    def Pointillism(commands, brushSize=None):
        import scipy.spatial as spatial

        maxRadius = brushSize if brushSize is not None else 8.0  # brush size
        positions = np.array([(c.x, c.y) for c in commands if c.hasFlag("contact")])
        point_tree = spatial.cKDTree(positions)

        r = point_tree.query_ball_tree(point_tree, maxRadius)
        rMap = [[idx, len(nb)] for idx, nb in enumerate(r)]
        rMap = list(sorted(rMap, key=lambda x: x[1], reverse=True))
        usedPoints = set()
        toUseAndIdx = []
        for idx, _ in rMap:
            if idx in usedPoints:
                toUseAndIdx.append([np.array([-999999, -999999]), -999999])
                continue
            nb = r[idx]
            toUseAndIdx.append([positions[idx], idx])
            for i in nb:
                usedPoints.add(i)
            if len(usedPoints) == len(positions):
                break

        toUse = [
            i[0] for i in list(sorted(toUseAndIdx, key=lambda x: x[1], reverse=True))
        ]

        new = []
        for i in range(len(toUse)):
            point = toUse[i]
            command = commands[i]
            if command.hasFlag("required"):
                new.append(command)
                continue

            if point[0] == -999999:
                continue

            new.append(
                Command(
                    x=point[0],
                    y=point[1],
                    z=BRUSH_HOLDER_ENTRY_Z,
                    f=10000,
                    flags=["adapter", "style", "pointillism"],
                )
            )

            new.append(
                Command(
                    x=point[0],
                    y=point[1],
                    z=BRUSH_TIP_Z_OFFSET - 2,
                    f=10000,
                    flags=["contact", "adapter", "style", "pointillism"],
                )
            )
            new.append(
                Command(
                    x=point[0],
                    y=point[1],
                    z=BRUSH_HOLDER_ENTRY_Z,
                    f=10000,
                    flags=["adapter", "style", "pointillism"],
                )
            )
        return new

    def Wavy(commands, maxOscillationDistance=30, numOscillations=None):
        def oscillationArray(max_oscillation, length, numOscillations=6):
            oscillations = np.linspace(0, numOscillations * np.pi, length)
            oscillation_values = np.sin(oscillations) * max_oscillation // 2
            # normalise the values to be between -max_oscillation/2 and max_oscillation/2
            normalised = (oscillation_values / max_oscillation) * max_oscillation
            # make all the values integer
            normalised = normalised.astype(int)
            return normalised

        positions = np.array([(c.x, c.y) for c in commands if c.hasFlag("contact")])

        if numOscillations is None:

            oscillations = max(int(len(positions) / 66.6), 1)
        else:
            oscillations = numOscillations
        osc = oscillationArray(maxOscillationDistance, len(positions), oscillations)
        for idx, c in enumerate(commands):
            if c.hasFlag("contact"):
                c.x += osc[idx]

        return commands
