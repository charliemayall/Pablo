import numpy as np
from dataclasses import dataclass
from typing import Optional
from PIL import Image, ImageDraw
from gcode import Command
from const import *
import math
import random


@dataclass
class HolderPosition:
    """
    HolderPosition class.
    """

    index: int  # the index of the holder, not the slot in the holder
    colorIdx: str
    brushes: Optional[list]
    x: float
    y: float

    def __str__(self):
        return f"HolderPosition({self.index}, {self.colorIdx}, {self.brushes})"

    def __repr__(self):
        return f"HolderPosition({self.index}, {self.colorIdx}, {self.brushes})"


class PaintPot:
    """
    PaintPot class.
    """

    def __init__(self, index, color=None):
        self.index = index
        self.color = color
        self.outToIn = False
        self.x = POT_BOARD_CORNER_X + (index * POT_SPACING) + 20 + POT_DIAMETER / 2
        self.y = POT_BOARD_CORNER_Y + (POT_BOARD_WIDTH / 2)
        self.safeX, self.safeY = self.x, self.y + POT_BOARD_WIDTH
        self.safeZ = -1
        self._inPotZ_c = Command(
            z=BRUSH_TIP_Z_OFFSET + (POT_HEIGHT - POT_DEPTH),
            f=BASE_FEED_RATE,
            flags=["required", "paintPot"],
        )
        self._spiralCoords = list(self.spiral_points(separation=2))
        self._scrape_c = self._scrape()
        self._enterScrape_c = self._scrape_c[: int(0.5 * len(self._scrape_c))]

    def use(self, nextMove: Command = None):

        base = (
            self._getToPotCenter()
            + self._enterScrape_c
            + self._swirl()
            + self._scrape_c
            + self._exitPot()
        )
        if nextMove is None:
            return base
        else:
            addMove = Command(
                x=nextMove.x,
                y=nextMove.y,
                z=0,
                f=BASE_FEED_RATE,
                flags=["contact"],  # have to flag as contact or it wont be mirrored
            )

            return base + [addMove]

    def _getToPotCenter(self):
        return [
            Command(z=self.safeZ, f=BASE_FEED_RATE, flags=["required", "paintPot"]),
            Command(
                x=self.safeX,
                y=self.safeY,
                f=BASE_FEED_RATE,
                flags=["required", "paintPot"],
            ),
            Command(
                x=self.x,
                y=self.y,
                z=self.safeZ,
                f=BASE_FEED_RATE,
                flags=["required", "paintPot"],
            ),
            Command(
                z=BRUSH_TIP_Z_OFFSET + POT_HEIGHT,
                f=BASE_FEED_RATE,
                flags=["required", "paintPot"],
            ),
        ]

    def _exitPot(self):
        return [
            Command(
                x=self.x, y=self.y, f=BASE_FEED_RATE, flags=["required", "paintPot"]
            ),
            Command(
                z=self.safeZ,
                f=BASE_FEED_RATE,
                flags=["required", "paintPot"],
            ),
            Command(
                x=self.safeX,
                y=self.safeY,
                f=BASE_FEED_RATE,
                flags=["required", "paintPot"],
            ),
        ]

    def _swirl(self):

        array = np.array(self._spiralCoords)
        array = (array - np.min(array)) / (np.max(array) - np.min(array))
        array = (array - 0.5) * (POT_DIAMETER - 8)
        baseZ = BRUSH_TIP_Z_OFFSET + 5
        zOscillate = [baseZ + i for i in range(-2, 2, 1)]
        zOscillateArr = np.repeat(zOscillate, len(array))
        commands = [
            Command(
                x=self.x + i[0],
                y=self.y + i[1],
                z=j,
                f=BASE_FEED_RATE,
                flags=["required", "paintPot"],
            )
            for i, j in zip(array, zOscillateArr)
        ]
        if self.outToIn:
            commands = commands[::-1]
            self.outToIn = False
        else:
            self.outToIn = True
        return [self._inPotZ_c] + commands

    def _scrape(self):
        # spiral around the edge of the pot while increasing z
        circleCoordsX = [
            math.cos(math.radians(i)) * (POT_DIAMETER - 8) / 2
            for i in np.linspace(0, 360)
        ]
        circleCoordsY = [
            math.sin(math.radians(i)) * (POT_DIAMETER - 8) / 2
            for i in np.linspace(0, 360)
        ]
        # circleCoords = np.array([circleCoordsX, circleCoordsY])
        commands = []
        numCoords = len(circleCoordsX)
        baseZ = BRUSH_TIP_Z_OFFSET + (POT_HEIGHT - POT_DEPTH)
        for z in range(baseZ + POT_HEIGHT - 30, baseZ + POT_HEIGHT - 10, 5):
            counter = 0
            if z > BED_MAX_Z:
                z = BED_MAX_Z - 1
            for x, y in zip(circleCoordsX, circleCoordsY):
                commands.append(
                    Command(
                        x=self.x + x,
                        y=self.y + y,
                        z=min(
                            z + (counter * 5 / numCoords), BED_MAX_Z - 1
                        ),  # to get a nice gradient
                        f=BASE_FEED_RATE,
                        flags=["required", "paintPot", "scrape"],
                    )
                )
                counter += 1

            if z == BED_MAX_Z - 1:
                break
        return commands

    def spiral_points(self, arc=1, separation=1):
        """generate points on an Archimedes' spiral
        with `arc` giving the length of arc between two points
        and `separation` giving the distance between consecutive
        turnings
        - approximate arc length with circle arc at given distance
        - use a spiral equation r = b * phi
        """

        def p2c(r, phi):
            """polar to cartesian"""
            return (r * math.cos(phi), r * math.sin(phi))

        # yield a point at origin
        yield (0, 0)

        # initialize the next point in the required distance
        r = arc
        b = separation / (2 * math.pi)
        # find the first phi to satisfy distance of `arc` to the second point
        phi = float(r) / b
        for i in range(200):
            yield p2c(r, phi)
            # calculate phi that will give desired arc length at current radius
            # (approximating with circle)
            phi += float(arc) / r
            r = b * phi


class PaintPotRandom(PaintPot):
    def use(self, nextMove: Command = None):
        base = (
            self._getToPotCenter()
            # + self._enterScrape_c
            + self._random_points_within_circle(
                10, (POT_DIAMETER - 8) / 2, (self.x, self.y)
            )
            + self._scrape()
            + self._exitPot()
        )
        if nextMove is None:
            return base
        else:
            addMove = Command(
                x=nextMove.x,
                y=nextMove.y,
                z=0,
                f=BASE_FEED_RATE,
                flags=["contact"],  # have to flag as contact or it wont be mirrored
            )

            return base + [addMove]

    def _scrape(self):
        angles = (0, 180,90, 270)
        center = (self.x, self.y)
        commands = []
        radius1 = (POT_DIAMETER - 8) / 2
        radius2 = (POT_DIAMETER + 8) / 2
        halfRad = (POT_DIAMETER - 8) / 4
        z1 = max(BRUSH_TIP_Z_OFFSET + POT_HEIGHT - 17, BED_MIN_Z)
        z2 = BED_MAX_Z
        for angle in angles:
            x1 = center[0] + radius1 * math.cos(math.radians(angle))
            y1 = center[1] + radius1 * math.sin(math.radians(angle))
            x2 = center[0] + radius2 * math.cos(math.radians(angle))
            y2 = center[1] + radius2 * math.sin(math.radians(angle))
            x3 = center[0] + halfRad * math.cos(math.radians(angle))
            y3 = center[1] + halfRad * math.sin(math.radians(angle))
            commands.append(
                Command(
                    x=x1, y=y1, z=z1, f=BASE_FEED_RATE, flags=["required", "paintPot"]
                )
            )
            commands.append(
                Command(
                    x=x2, y=y2, z=z2, f=BASE_FEED_RATE, flags=["required", "paintPot"]
                )
            )
            commands.append(
                Command(
                    x=x3, y=y3, z=z2, f=BASE_FEED_RATE, flags=["required", "paintPot"]
                )
            )
        return commands

    def _random_points_within_circle(self, num_points, radius, center):
        """generate random points within a circle
        with given radius and center
        """
        commands = []
        for i in range(num_points):
            # generate random angle
            angle = random.uniform(0, 2 * math.pi)
            # generate random radius
            _r = random.uniform(0, radius)
            # calculate x and y coordinates
            x = center[0] + _r * math.cos(angle)
            y = center[1] + _r * math.sin(angle)
            commands.extend(
                [
                    Command(
                        x=x,
                        y=y,
                        z=BRUSH_TIP_Z_OFFSET + 5,
                        f=BASE_FEED_RATE,
                        flags=["required", "paintPot"],
                    ),
                ]
            )

        return commands


class Brush:
    """
    Brush class.
    """

    def __init__(
        self, size, holder: HolderPosition, holderSlotIndex: int, paintPot: PaintPot
    ):

        self.paintPot = paintPot
        self.size = size
        self.holder = holder
        self.holderSlotIndex = holderSlotIndex
        self.used = False
        self.corner, self.entrance, self.brushPos = None, None, None
        self._calcPositions()
        self._init_general_commands()
        self._getMaxStrokeLength()

    def __str__(self):
        return f"Brush: {self.colorIdx} {self.size} {self.holderIdx}"

    def __repr__(self):
        return f"""Brush(colorIdx={self.colorIdx}, size={self.size}, holderIdx={self.holderIdx}),
        maxStrokeLength={self.maxStrokeLength}"""

    def refill(self, *args, **kwargs):
        return self.paintPot.use(*args, **kwargs)

    def _getMaxStrokeLength(self):
        # These are just approximate lengths for each brush
        # Requires brush in holderSlotIndex 0 to be largest, and the brush in 2 to be smallest
        self.maxStrokeLength = [650, 300, 150][self.holderSlotIndex]

    def _calcPositions(self):
        """
        Calculate the positions of the brush.
        """
        halfArmWidth = 7
        offsets = {
            # edited
            0: {
                "entrance": [self.holder.x + 25 + halfArmWidth, self.holder.y + 40],
                "corner": [self.holder.x + 25 + halfArmWidth, self.holder.y - 2],
                "brushPos": [self.holder.x + 10 + halfArmWidth, self.holder.y - 2],
            },
            1: {
                "entrance": [self.holder.x + 64 + halfArmWidth, self.holder.y + 40],
                "corner": [self.holder.x + 64 + halfArmWidth, self.holder.y - 2],
                "brushPos": [self.holder.x + 51 + halfArmWidth, self.holder.y - 2],
            },
            2: {
                "entrance": [self.holder.x + 96.3 + halfArmWidth, self.holder.y + 40],
                "corner": [self.holder.x + 96.3 + halfArmWidth, self.holder.y + 1.77],
                "brushPos": [
                    self.holder.x + 86.3 + halfArmWidth - 3,
                    self.holder.y + 1.77,
                ],
            },
        }
        offset = offsets[self.holderSlotIndex]
        self.entrance = Command(
            x=offset["entrance"][0],
            y=offset["entrance"][1],
            z=BRUSH_HOLDER_ENTRY_Z,
            f=BASE_FEED_RATE,
            flags=["required", "brushChange"],
        )
        self.corner = Command(
            x=offset["corner"][0],
            y=offset["corner"][1],
            z=BRUSH_HOLDER_ENTRY_Z,
            f=HOLDER_FEED_RATE,
            flags=["required", "brushChange"],
        )
        self.brushPos = Command(
            x=offset["brushPos"][0],
            y=offset["brushPos"][1],
            z=BRUSH_HOLDER_ENTRY_Z,
            f=HOLDER_FEED_RATE,
            flags=["required", "brushChange"],
        )

        return self.entrance, self.corner, self.brushPos

    def pickup(self, isFirst=False):
        return self._pickup if isFirst else self._pickup[1:]

    def drop(self):
        return self._dropoff

    def _init_general_commands(self):
        setup = Command(y=300, z=-45, f=BASE_FEED_RATE)
        get_safe_z = Command(z=0, f=BASE_FEED_RATE)
        get_safe_xy = Command(
            x=self.entrance.x, y=60 + 38 + 15, f=BASE_FEED_RATE
        )  # entrance y has 40 added to it already
        get_entry_z = Command(z=BRUSH_HOLDER_ENTRY_Z, f=BASE_FEED_RATE)
        into_entrance = Command(y=60 + 38, f=HOLDER_FEED_RATE)
        to_corner = Command(x=self.entrance.x, y=self.corner.y, f=HOLDER_FEED_RATE)
        to_brush_pos = Command(x=self.brushPos.x, y=self.brushPos.y, f=HOLDER_FEED_RATE)
        down_a_bit = Command(z=BRUSH_HOLDER_ENTRY_Z - 2.25, f=HOLDER_FEED_RATE)
        pull_back = Command(y=60 + 38 + 15, f=BASE_FEED_RATE)
        to_pot_center = Command(x=self.paintPot.x, y=self.paintPot.y, f=BASE_FEED_RATE)
        get_safe_brushPos_xy = Command(
            x=self.brushPos.x,
            y=60 + 38 + 15,
            f=BASE_FEED_RATE,
        )  # entrance y has 40 added to it already
        toBrushPos = Command(x=self.brushPos.x, y=self.brushPos.y, f=HOLDER_FEED_RATE)
        toCorner = Command(x=self.corner.x, y=self.corner.y, f=HOLDER_FEED_RATE)
        toEntrance = Command(y=60 + 38, f=HOLDER_FEED_RATE)

        self._pickup = [
            setup,
            get_safe_z,
            to_pot_center,
            get_safe_brushPos_xy,
            get_entry_z,
            toBrushPos,
            toCorner,
            toEntrance,
            get_safe_xy,
            get_safe_z,
            to_pot_center,  # maybe change this, we never pick it up and dont add paint
        ]
        for command in self._pickup:
            command.flags.extend(["required", "brushChange", "pickup"])
        self._dropoff = [
            get_safe_z,
            get_safe_xy,
            get_entry_z,
            into_entrance,
            to_corner,
            to_brush_pos,
            down_a_bit,
            pull_back,
            get_safe_z,
            to_pot_center,  # always refill brush after pickup
        ]
        for command in self._dropoff:
            command.flags.extend(["required", "brushChange", "drop"])


@dataclass
class PablosHand:
    """
    wrapper for the "print head"

    """

    x: float
    y: float
    z: float
    currentBrush: Optional[Brush] = None
    currentPaintPot: Optional[PaintPot] = None

    def __str__(self):
        return f"PablosHand: {self.x} {self.y} {self.z} {self.currentBrush}"

    def __repr__(self):
        return f"PablosHand(x={self.x}, y={self.y}, z={self.z}, currentBrush={self.currentBrush})"


@dataclass
class Tracker:
    """
    Tracker class.
    Used to keep track of stroke length for refilling the paint brush
    """

    length: float = 0
    moves: list = None
    canvas: Image = None

    def __str__(self):
        return f"Tracker: {self.id} {self.length} {self.moves}"

    def __repr__(self):
        return f"Tracker(id={self.id}, length={self.length}, moves={self.moves})"

    def add(self, move, color=False):
        if self.moves is None:
            self.moves = []
        if len(self.moves) == 0:
            self.moves.append(move)
        else:
            try:
                lastMove = self.moves[-1]
                length = lastMove.distanceTo(move)
                self.length += length
                self.moves.append(move)

                ImageDraw.Draw(self.canvas).line(
                    (lastMove.x, lastMove.y, move.x, move.y),
                    fill="green" if not color else color,
                    width=1,
                )
            except Exception as e:
                print(e)
                print(f"lastMove: {lastMove}")
                print(f"move: {move}")
                print(f"length: {length}")
        return self.length

    def show(self):
        self.canvas.show()
