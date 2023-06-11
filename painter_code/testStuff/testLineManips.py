import black
import numpy as np
from PIL import Image, ImageDraw
import math
from pathlib import Path
from scipy.spatial import cKDTree
from wrappers import Command
import json

ROOT = Path(__file__).parent
with open(ROOT / "c_data.json") as r:
    data = json.load(r)

commands = [
    Command(x=item["x"], y=item["y"], z=item["z"], f=item["f"], flags=item["flags"])
    for item in data
]
idxOrderMap = []
xyCoords = []
for command in commands:
    xyCoords.append((command.x, command.y))


def find_shortest_path(xy_points):
    """
    Find the shortest path between two points.
    """
    points = np.array(xy_points)
    points = [point for point in points if not np.isnan(point).any()]
    tree = cKDTree(points)
    consumed = set()
    retPoints = [points[0]]
    retIdx = [0]
    lenP = len(points)
    point = points.pop(0)
    iterNum = 0
    while iterNum < lenP:
        neighbours = tree.query(point, k=lenP - 1)
        for idx in neighbours[1]:
            if idx in consumed:
                continue
            retPoints.append(tree.data[idx])
            retIdx.append(idx)
            consumed.add(idx)
            point = tree.data[idx]
            break
        iterNum += 1
    return retPoints, retIdx


def find_path_distance(coordinates):
    """
    Find the distance of the path.
    """
    dist = 0
    dist2 = 0
    toConsider = [point for point in coordinates if not np.isnan(point).any()]
    if not isinstance(toConsider[0], np.ndarray):
        toConsider = np.array(toConsider)
    for i in range(len(toConsider) - 1):
        dist += np.linalg.norm(toConsider[i] - toConsider[i + 1])
        dist2 += math.sqrt(
            (toConsider[i][0] - toConsider[i + 1][0]) ** 2
            + (toConsider[i][1] - toConsider[i + 1][1]) ** 2
        )
    print(dist)
    print(dist2)


def excludePointsWithin(tree: cKDTree, radius=0.2):
    consumed = set()
    retPoints = []
    retIndicies = []
    idx = 0
    for idx, point in enumerate(tree.data):
        if idx in consumed:
            continue
        if any(np.isnan(point)):
            retPoints.append(point)
            retIndicies.append(idx)
            continue
        neighbours = tree.query_ball_point(point, radius)
        if not neighbours:
            retPoints.append(point)

        else:
            xSum = sum([tree.data[i][0] for i in neighbours])
            ySum = sum([tree.data[i][1] for i in neighbours])
            avgX = xSum / len(neighbours)
            avgY = ySum / len(neighbours)
            retPoints.append([avgX, avgY])
            retIndicies.append(idx)
            for i in neighbours:
                consumed.add(i)
        consumed.add(idx)
        idx += 1
    return retPoints, retIndicies


tree = cKDTree(xyCoords)
rP, rI = excludePointsWithin(tree)
print(len(xyCoords), len(rP))
sP, sI = find_shortest_path(rP)
print(find_shortest_path(np.array(xyCoords)))
print(find_path_distance(rP))
print(find_path_distance(sP))
newCommands = [commands[i] for i in rI]
print(1)
