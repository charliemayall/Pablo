from copyreg import pickle
from gcode import Command
from const import *
from session import SerialSession
from main import Backend
import commandAdapters as CA
import json
from wrappers import HolderPosition, Brush, PaintPot
from pathlib import Path

ROOT = Path(__file__).parent
SESSION = SerialSession()

config = json.load(open(ROOT / "configs/brushHolderConfig.json"))

pot = PaintPot(0)


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
            brush = Brush(**brushData, holder=tempHolder, paintPot=pot)
            brush.holder = tempHolder
            tempHolder.brushes.append(brush)
        holderPositions.append(tempHolder)
    return holderPositions


def makeCommand():
    attrs = {}
    for attr in ["x", "y", "z"]:
        conf = ".."
        while not "Y" in conf.upper():
            _ = input(f"{attr}: ")
            conf = input(f"{attr}={_} (Y/n): ")
        attrs[attr] = float(_)
    attrs["f"] = 10000
    command = Command(**attrs)
    print("Created Command")
    print(repr(command))
    return command


position = makeHolderPositions(config)[0]
brush = position.brushes[0]
brush2 = position.brushes[1]

##### DROP OFF ####
setup = Command(y=300, z=-45, f=10000)
get_safe_z = Command(z=0, f=8000)
get_safe_xy = Command(
    x=brush.entrance.x, y=60 + 38 + 15, f=8000
)  # entrance y has 40 added to it already
get_entry_z = Command(z=BRUSH_HOLDER_ENTRY_Z, f=4000)
into_entrance = Command(y=60 + 38, f=4000)
to_corner = Command(x=brush.entrance.x, y=brush.corner.y, f=2000)
to_brush_pos = Command(x=brush.brushPos.x, y=brush.brushPos.y, f=2000)
down_a_bit = Command(z=BRUSH_HOLDER_ENTRY_Z - 2.25, f=2000)
pull_back = Command(y=60 + 38 + 15, f=4000)
past_pots = Command(y=60 + POT_BOARD_WIDTH + 38 + 60, f=4000)

DROPOFF = [
    setup,  # ONLY IF IT IS THE FIRST BRUSH, not necessary in actual code
    get_safe_z,
    get_safe_xy,
    get_entry_z,
    into_entrance,
    to_corner,
    to_brush_pos,
    down_a_bit,
    pull_back,
    get_safe_z,
    past_pots,
]


########### PICK UP #############

get_safe_brushPos_xy = Command(
    x=brush.brushPos.x, y=60 + 38 + 15, f=8000
)  # entrance y has 40 added to it already
toBrushPos = Command(x=brush.brushPos.x, y=brush.brushPos.y, f=2000)
toCorner = Command(x=brush.corner.x, y=brush.corner.y, f=2000)
toEntrance = Command(y=60 + 38, f=4000)

PICKUP = [
    setup,  # ONLY IF IT IS THE FIRST BRUSH
    get_safe_z,
    get_safe_brushPos_xy,
    get_entry_z,
    toBrushPos,
    toCorner,
    toEntrance,
    get_safe_xy,
    get_safe_z,
    past_pots,  # maybe change this, we never pick it up and dont add paint
]

SESSION.safeWrite(brush.pickup())
SESSION.safeWrite(brush.drop())
SESSION.safeWrite(brush2.pickup())
SESSION.safeWrite(brush2.drop())
