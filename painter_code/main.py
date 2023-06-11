import asyncio
from preprocess import PreProcessors
from gcode import GcodeMaker, Command
import commandAdapters as CA
from const import *
from wrappers import (
    PablosHand,
    PaintPot,
    HolderPosition,
    Brush,
    Tracker,
    PaintPotRandom,
)
from session import SerialSession
from pathlib import Path
import json
from PIL import Image
import websockets
from websockets.exceptions import ConnectionClosedError
import logging
import time

PaintPot = PaintPotRandom

KILL_EVENT = asyncio.Event()
ROOT = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s -: %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "logs/pablo_log.txt"),
        logging.StreamHandler(),
    ],
)


class Backend:
    def __init__(
        self,
        brushConfig,
        holderConfig,
        serialSession: SerialSession,
        potConfig=None,
        commandAdapters=None,
        strokeAdapters=None,
        preprocessors=None,
    ):
        self.log = logging.getLogger("backend")
        self.session = serialSession
        self.commandAdapters = commandAdapters if commandAdapters else []
        self.strokeAdapters = strokeAdapters if strokeAdapters else []
        self.preprocessors = preprocessors if preprocessors else []
        self.needsKill = False
        self.tracker = Tracker(
            length=0,
            canvas=Image.new(
                "RGB", (BED_MAX_X - BED_MIN_X, BED_MAX_Y - BED_MIN_Y), (255, 255, 255)
            ),
        )
        if isinstance(potConfig, str):
            with open(Path(potConfig)) as f:
                self.pots = [PaintPot(**pot) for pot in json.load(f)]

        elif isinstance(potConfig, list):
            self.pots = [PaintPot(**p) for p in potConfig]
        else:
            self.pots = [PaintPot(index=i, color=None) for i in range(6)]
        with open(holderConfig) as f:
            config = json.load(f)

        self.holders = self.makeHolderPositions(config)
        if len(self.holders) == 0:
            raise Exception("No holders found")
        self.log.info("test")
        self.hand = PablosHand(
            x=0,
            y=0,
            z=0,
            currentBrush=None,
            currentPaintPot=self.pots[0],
        )

    def applyCommandAdapters(self, commands):
        if self.commandAdapters is not None:
            for adapter in self.commandAdapters:
                commands = adapter(commands)
                self.log.info(
                    f"Command Adapter:{adapter.__name__} applied -> {len(commands)} commands"
                )

        return commands

    def makeHolderPositions(self, config):
        """
        Create the holder positions from the config.
        """
        holderPositions = []
        for holderData in config:
            brushes = holderData.pop("brushes")
            holderData["brushes"] = []
            tempHolder = HolderPosition(**holderData)
            for idx, brushData in enumerate(brushes):
                paintPot = self.pots[tempHolder.index]
                brush = Brush(**brushData, paintPot=paintPot, holder=tempHolder)

                tempHolder.brushes.append(brush)
            holderPositions.append(tempHolder)
        return holderPositions

    def handleGCode(self, streamLines: list) -> list:
        """
        Handle the gcode lines.
        """
        self.log.info(f"{len(streamLines)} lines recieved")
        gcodeMaker = GcodeMaker()
        gcodeMaker.parse(streamLines)
        baseCommands = self.applyPreProcessors(gcodeMaker.commands)
        self.log.info(
            f"Preprocessed {len(gcodeMaker.commands)} commands -> {len(baseCommands)}"
        )

        baseCommands = self._handleStrokeLength(baseCommands)
        commands = self.applyCommandAdapters(baseCommands)
        self.log.info(f"{len(commands)} commands produced")
        return commands

    def applyPreProcessors(self, commands: "list[Command]") -> "list[Command]":
        """
        Apply changes to commands produced by GcodeMaker,
        before anything such as refill, brush, and lift-off commands are added
        """
        for pp in self.preprocessors:
            commands = pp(commands)
        return commands

    def _handleStrokeLength(self, commands: "list[Command]") -> "list[Command]":
        """
        Add refills to the commands.
        NOTE: the commands MUST be just those from the raw data, parsed by gcodeMaker.
        Any commands added by adapters, or by this class, may be removed
        """
        # find the total length of the stroke
        returnCommands = []

        limit = self.hand.currentBrush.maxStrokeLength
        total = 0
        distVals = []
        filtCommands = list(filter(lambda c: c.hasFlag("contact"), commands))
        if self.tracker.length > limit:
            self.log.info(
                f"Refill, reason = Leftover stroke length from previous stroke"
            )
            refillCommands = self.hand.currentBrush.refill(nextMove=filtCommands[0])
            returnCommands.extend(refillCommands)
            self.tracker.length = 0
        total += self.tracker.length
        hasStartRefill = False
        self.log.info(f"Total length: {total}, limit: {limit}")
        if not len(filtCommands) == len(commands):
            self.log.warning(
                """_handleStrokeLength: commands removed by filtering,
                commands passed to this function should not include anything
                other than those produced by gcodeMaker"""
            )

        for i, command in enumerate(filtCommands[:-1]):
            dist = command.distanceTo(filtCommands[i + 1])
            distVals.append(dist)
            total += dist

        if (
            limit * 0.9 < total < limit * 1.1 and returnCommands == []
        ):  # check that returnCommands is empty
            # (not added to by the self.tracker.length > limit block)
            self.log.info("Refill, reason = Stroke length is within 10% of limit")
            refillCommands = self.hand.currentBrush.refill(nextMove=filtCommands[0])

            self.tracker.length = 0
            returnCommands.extend(commands)
            returnCommands.extend(refillCommands)
            return returnCommands

        elif total > limit:
            for i, command in enumerate(filtCommands):
                self.tracker.add(command)

                if self.tracker.length > self.hand.currentBrush.maxStrokeLength:
                    # if the remaining stroke length is less that 25% of the max stroke length,
                    # just refill at the start of next stroke
                    if (
                        sum(distVals[i:])
                        < 0.25 * self.hand.currentBrush.maxStrokeLength
                    ):
                        self.log.info(
                            """Skipping Refill, reason = remainder of stroke exceeds
                            max stroke length by less than 25%"""
                        )
                        # add the rest of the commands we havent iterated over
                        for c in filtCommands[i:]:
                            self.tracker.add(c)
                        returnCommands.extend(filtCommands[i:])
                        # dont reset tracker length, so will refill next stroke start
                        return returnCommands
                    # if we exceed the max length within the first 25% of the stroke,
                    # refill at the start of the stroke
                    elif (
                        sum(distVals[:i]) < 0.25 * sum(distVals) and not hasStartRefill
                    ):
                        self.log.info(
                            """Refill, reason = refilling at start of stroke as stroke length
                            exceeded within the first 25% of the stroke"""
                        )
                        # add the rest of the commands we havent iterated over
                        returnCommands.append(command)
                        refillCommands = self.hand.currentBrush.refill(nextMove=command)

                        # add the refill commands to the start of returnCommands
                        returnCommands = refillCommands + returnCommands
                        self.tracker.length = 0
                        hasStartRefill = True
                    # otherwise, simply add a refill step before the current command
                    else:
                        self.log.info(
                            f"""Refill, reason = Stroke length is over limit
                            ({self.tracker.length} > {self.hand.currentBrush.maxStrokeLength})"""
                        )
                        returnCommands.append(command)
                        refillCommands = self.hand.currentBrush.refill(nextMove=command)
                        returnCommands.extend(refillCommands)
                        self.tracker.length = 0

                returnCommands.append(command)
            return returnCommands
        else:
            return commands

    def swapBrush(self, colorIdx, sizeIdx):
        sizeIdx = int(sizeIdx)
        colorIdx = int(colorIdx)
        commands = []
        if self.hand.currentBrush is not None:
            self.log.info(
                f"Drop commands issued for brush {self.hand.currentBrush.size}"
            )
            commands.extend(self.hand.currentBrush.drop())
        newBrush = None
        for holder in self.holders:
            # colorIdx is the same as the holder index,
            # as it doesnt really matter what color is used for each holder,
            # as long as it is only used for that holder
            if holder.index == colorIdx:
                # -sizeIdx as our index starts with big brush, the app starts with small.
                newBrush = holder.brushes[sizeIdx]
                self.log.info(f"New brush selected {newBrush.size}")
                break
        else:
            self.log.warning(f"No holder found for color {colorIdx} and size {sizeIdx}")
            newBrush = self.holders[0].brushes[0]

        newBrush.used = True
        # get the new brush
        commands.extend(newBrush.pickup(isFirst=self.hand.currentBrush is None))
        self.log.info(f"Pick up commands issued for brush {newBrush.size}")
        # fill it with paint
        commands.extend(newBrush.refill())
        self.hand.currentBrush = newBrush
        self.log.info(f"Refill commands issued for brush {newBrush.size}")
        self.tracker.length = 0
        return commands

    def run(self, streamData):
        """
        Run a single input.
        """
        if self.needsKill:
            return
        allCommands = []

        # setup for color and brush
        size = float(streamData["size"].split(" ")[1])
        sizeIdx = 3 - int(streamData["size"].split(" ")[0])
        colorIdx = int(streamData["color"].split(" ")[0]) - 1
        lines = streamData["data"]
        self.log.info(
            f"""Stream recieved: lines={len(lines)}, size={size},
            sizeIdx={sizeIdx},colorIdx={colorIdx}"""
        )
        if self.hand.currentBrush is None:
            self.log.info(f"No brush selected, selecting brush {size}")
            commands = self.swapBrush(colorIdx, sizeIdx)
            allCommands.extend(commands)

        elif (
            sizeIdx != self.hand.currentBrush.holderSlotIndex
            or colorIdx != self.hand.currentBrush.paintPot.index
        ):
            allCommands.extend(self.swapBrush(colorIdx, sizeIdx))
            self.log.info(f"Changing brush to {size} {colorIdx}")

        strokeCommands = self.handleGCode(lines)
        allCommands.extend(strokeCommands)
        return allCommands

    def shutdown(self):
        """
        Shutdown the hand.
        """
        KILL_EVENT.set()
        self.needsKill = True
        commands = []
        if self.hand.currentBrush is not None:
            self.log.info("Shutdown: Putting brush back in holder")
            commands.extend(self.hand.currentBrush.drop())
            self.session.safeWrite(commands)
        self.session.home()
        return True


async def producer(queue):
    logger = logging.getLogger("producer")

    async def toQueue(res):
        decoded = json.loads((json.loads(res))["data"])
        decoded["data"] = json.loads(decoded["data"])
        await queue.put(decoded)

    while True:
        async with websockets.connect("---REDACTED---") as websocket:
            while not KILL_EVENT.is_set():
                try:
                    res = await asyncio.wait_for(websocket.recv(), timeout=10)
                    logger.info("Recieved Data")
                    await toQueue(res)
                    logger.info("Data queued")
                except ConnectionClosedError:
                    logger.warning("WebSocket Connection closed")
                    break
                except asyncio.TimeoutError:
                    pass


async def consumer(queue, session, handler: Backend):
    logger = logging.getLogger("consumer")
    i = 0
    while not session.ready:
        time.sleep(0.2)
        if i % 30 == 0:
            print("waiting")
            i = 0
        i += 1

    while not KILL_EVENT.is_set():
        data = await queue.get()
        logger.info("Data recieved from queue")
        commands = handler.run(data)
        logger.info("Data processed")
        res = session.safeWrite(commands)

        if "ALARM" in res:
            logger.critical(
                f"ALARM: {res}\nFrom commands: {''.join([str(c) for c in commands])}"
            )
        logger.info("Data sent to arduino")

        print(res)
        handler.log.info("Commands sent")

        queue.task_done()


def test(test_data):
    if not isinstance(test_data, list):
        test_data = [test_data]
    logger = logging.getLogger("main")
    logger.info("Starting main")

    HANDLER = Backend(
        brushConfig=str(ROOT / "configs/brushConfig.json"),
        holderConfig=str(ROOT / "configs/brushHolderConfig.json"),
        serialSession=None,
        commandAdapters=[CA.startAndEndLift, CA.mirrorOnY, CA.checkLimits],
    )
    SESSION = SerialSession()
    for item in test_data:
        commands = HANDLER.run(item)
        with open(ROOT / "test_command_output.txt", "a+") as f:
            for c in commands:
                f.write(repr(c) + "\n")
        SESSION.safeWrite(commands)


def testCreator():
    from testStuff import dataCreators

    circle_stack = dataCreators.CircleStack.create(6, 75, (300, 650))
    for item in circle_stack:
        item.update({"color": "1 0xff000000"})

    test(circle_stack)


async def main(event=None):
    logger = logging.getLogger("main")
    logger.info("Starting main")
    global queue
    queue = asyncio.Queue(maxsize=0)
    SESSION = SerialSession()
    HANDLER = Backend(
        brushConfig=str(ROOT / "configs/brushConfig.json"),
        holderConfig=str(ROOT / "configs/brushHolderConfig.json"),
        serialSession=SESSION,
        commandAdapters=[CA.startAndEndLift, CA.mirrorOnY, CA.checkLimits],
        preprocessors=[PreProcessors.excludePointsWithin, PreProcessors.modFeedRate],
    )
    producers = [asyncio.create_task(producer(queue))]
    consumers = [asyncio.create_task(consumer(queue, SESSION, HANDLER))]
    if event is not None:
        event.cont = HANDLER
        event.set()

    await asyncio.gather(*producers)

    await queue.join()

    for c in consumers:
        c.cancel()


if __name__ == "__main__":
    asyncio.run(main())
