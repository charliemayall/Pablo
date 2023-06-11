MAX_BUFFER_SIZE = 128
MAX_FEED_RATE = 14000

POT_BOARD_CORNER_X = 128.5  # corner nearest home in the X
POT_BOARD_CORNER_Y = 128  # corner nearest home
POT_BOARD_WIDTH = 110
POT_BOARD_THICKNESS = 8
POT_DIAMETER = 75
POT_HEIGHT = 45
POT_DEPTH = 30
POT_SPACING = 117.3


BRUSH_TIP_Z_OFFSET = -58

BRUSH_HOLDER_OFFSET_X = 0  # offset of the position where the brush is held on the head, from where the software considers the head to be
BRUSH_HOLDER_OFFSET_Y = 0
BRUSH_HOLDER_OFFSET_Z = 0
BRUSH_HOLDER_ENTRY_Z = (
    -45.16
)  # safe height for the brush gripper to move into the gap between the holder plates
BRUSH_BACKOFF_Z = -15  # safe height for the brush to lift at the end of a stroke

# usable area of the bed, including the area where the pots and shelf thing are
BED_MAX_X = 0
BED_MIN_X = -800
BED_MAX_Y = -65
BED_MIN_Y = -1198
BED_MAX_Z = 0
BED_MIN_Z = -80


# stroke length before refill in mm
MAX_STROKE_LENGTH = 999999999
BASE_FEED_RATE = 12000
HOLDER_FEED_RATE = 6000

ARANDOMNUMBER = 589231
