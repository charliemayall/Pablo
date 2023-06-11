import numpy as np
from PIL import Image
from pathlib import Path
import json
import math

ROOT = Path(__file__).parent


class picConvert:
    def get_image(path):
        img = Image.open(path)
        img = img.convert("RGB")
        return img

    def to_black_and_white(img):
        img = img.convert("L")
        return img

    def main(path):
        img = get_image(path)
        img = to_black_and_white(img)
        img = img.resize((200, 200))
        pixels = np.array(img)
        # add 300 to the y axis
        all_data = []
        json_coords_black = {"color": "1 0xff000000", "size": "2 6.0", "data": []}
        # find the indicies of black pixels
        black_pixels = np.where(pixels < 128)
        # convert the indicies to a list of tuples
        black_pixels = list(zip(150 + black_pixels[0], 300 + black_pixels[1]))
        # find the indicies of white pixels
        white_pixels = np.where(pixels <= 128)
        # convert the indicies to a list of tuples
        white_pixels = list(zip(150 + white_pixels[0], 300 + white_pixels[1]))

        json_coords_white = {"color": "2 0xff000000", "size": "2 6.0", "data": []}
        for x, y in black_pixels:
            temp_data = json_coords_black.copy()
            temp_data["data"].append(f"{x} {y} 1 116")
            all_data.append(temp_data)
        for x, y in white_pixels:
            temp_data = json_coords_white.copy()
            temp_data["data"].append(f"{x} {y} 1 116")
            all_data.append(temp_data)
        data = [json_coords_black, json_coords_white]
        with open(ROOT / "test_from_img.json", "w") as f:
            f.write(json.dumps(data))
        return data


class CircleStack:
    def create(num, max_radius, center):
        data = []
        radius_increment = max_radius / num
        for i in range(num):
            color = 1 if i % 2 == 0 else 2
            radius = max_radius - (radius_increment * i)
            data.append(
                {
                    "color": f"{color} 0xff000000",
                    "size": "2 6.0",
                    "data": CircleStack.circleCoordinates(radius, center),
                }
            )
        return data

    def circleCoordinates(radius, center):
        data = []
        for i in range(360):
            x = radius * math.cos(math.radians(i)) + center[0]
            y = radius * math.sin(math.radians(i)) + center[1]
            data.append(f"{x} {y} 1 116")
        return data
