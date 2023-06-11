from scipy.spatial import cKDTree
import numpy as np
import logging
from const import *
LOGGER = logging.getLogger(__name__)


class PreProcessors:
    def excludePointsWithin(commands, radius=1):
        consumed = set()
        retPoints = []
        retIndicies = []
        idx = 0
        xyToConsider = [
            (c.x, c.y) for c in commands if c.x is not None and c.y is not None
        ]
        if len(xyToConsider) != len(commands):
            LOGGER.info("Warning: some commands have no xy")

        tree = cKDTree(xyToConsider)
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
        newCommands = [commands[i] for i in retIndicies]
        LOGGER.info("Reduced {} commands to {}".format(len(commands), len(newCommands)))
        return newCommands

    def modFeedRate(commands, factor=0.6):
        for c in commands:
            c.f = min([c.f * factor, MAX_FEED_RATE])
        return commands