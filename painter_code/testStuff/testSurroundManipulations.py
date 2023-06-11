import black
import numpy as np
from PIL import Image, ImageDraw
import math


def getPixelWindowAtCenter(w, h, center, img):
    if any(
        [
            x - w // 2 < 0,
            x + w // 2 >= img.shape[0],
            y - h // 2 < 0,
            y + h // 2 >= img.shape[1],
        ]
    ):
        return None
    x = center[0]
    y = center[1]
    x1 = x - w // 2
    x2 = x + w // 2
    y1 = y - h // 2
    y2 = y + h // 2
    return img[y1:y2, x1:x2]


def oscillationArray(max_oscillation, length, numOscillations=6):
    oscillations = np.linspace(0, numOscillations * math.pi, length)
    oscillation_values = np.sin(oscillations) * max_oscillation // 2
    # normalise the values to be between -max_oscillation/2 and max_oscillation/2
    normalised = (oscillation_values / max_oscillation) * max_oscillation
    # make all the values integer
    normalised = normalised.astype(int)
    return normalised


whiteImage = Image.new("RGB", (400, 400), (255, 255, 255))

draw = ImageDraw.Draw(whiteImage)
draw.line((0, 0, 400, 400), fill=(0, 0, 0), width=1)
whiteImage = np.array(whiteImage)
blackPx = np.where(np.all(whiteImage == 0, axis=-1))
osc = oscillationArray(50, len(blackPx[0]), 10)
# for each black pixel, move it along the x axis by the oscillation value
for x, y in zip(blackPx[0], blackPx[1]):
    x += osc[x]
    whiteImage[x, y] = (255, 0, 0)


pilImg = Image.fromarray(whiteImage)
pilImg.show()
