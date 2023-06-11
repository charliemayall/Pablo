# make a tkinter gui
import tkinter as tk
import asyncio
import logging
from pathlib import Path
import main as Painter
from PIL import ImageTk, Image, ImageOps
import os

if os.environ.get("DISPLAY", "") == "":
    print("no display found. Using :0.0")
    os.environ.__setitem__("DISPLAY", ":0.0")
ROOT = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s -: %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "logs/pablo_log.txt"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def do_stuff_after_x_seconds(timeout, stuff):
    for i in range(timeout):
        await asyncio.sleep(1)
        print(f"{i} seconds have passed")
    await asyncio.sleep(1)
    await stuff()
    return True


class Proc:
    isAlive = False

    def __init__(self):
        pass

    async def spawn(self):
        self.isAlive = True

        event = asyncio.Event()
        res_gen = Painter.main(event=event)
        await event.wait()
        res = False
        while not res:
            res = await res_gen.__anext__()

        print(res)
        print("task")
        return True

    async def kill(self, handler):
        self.isAlive = False
        event = asyncio.Event()
        handler.kill()
        return True


class Logo(tk.Frame):
    def __init__(self, root):
        tk.Frame.__init__(self, root)
        img = Image.open(str(ROOT / "logo.png"))
        img = ImageOps.contain(img, (400, 400))
        self.img = ImageTk.PhotoImage(img)
        self.label = tk.Label(self, image=self.img, bg="#777577")
        self.label.img = self.img
        self.configure(width=img.width, height=img.height)
        self.label.pack(anchor="nw", fill="both", expand=True)
        self.place(anchor="nw", relx=0.02, rely=0.02)


class ButtonToggles(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.backendHandler = None
        self.active = False
        self.disabled = False
        self.proc = None
        self.start_button = tk.Frame(self, bg="#5CFD2C", width=250, height=180)
        self.stop_button = tk.Frame(self, bg="#FF0000", width=250, height=180)
        self.start_button.pack(side="top", expand=False)
        self._makeBinds()

    def _makeBinds(self):
        self.start_button.bind("<Button-1>", self.onBtnDown)
        self.stop_button.bind("<Button-1>", self.onBtnDown)

    def toggleBtns(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._toggleBtns())

    async def _toggleBtns(self, *args):
        if self.disabled:
            return
        self.disabled = True
        if not self.active:
            await self.handleSpawn()
            self.active = True
        else:
            await self.handleKill()
            self.active = False
        self.disabled = False

    async def handleSpawn(self):
        logger.info("Spawning")
        self.isAlive = True
        self.start_button.pack_forget()
        await asyncio.sleep(1)
        event = asyncio.Event()
        event.cont = None
        self.task = asyncio.create_task(Painter.main(event=event))
        await event.wait()
        self.backendHandler = event.cont
        self.stop_button.pack(side="top", expand=False)

        return True

    async def handleKill(self):
        logger.info("Killing")
        self.stop_button.pack_forget()
        await asyncio.sleep(1)
        self.backendHandler.shutdown()
        self.start_button.pack(side="top", expand=False)
        self.active = False

        return True

    def onBtnDown(self, *args):
        self.toggleBtns()


class MainContainer(tk.Frame):
    def __init__(self, root):
        tk.Frame.__init__(self, root)
        self.configure(
            width=root.winfo_width(), height=root.winfo_height(), background="#777577"
        )


def on_closing(root, *args, **kwargs):
    root.destroy()
    pass


def main():
    root = tk.Tk()
    root.title("Painter")
    root.geometry("800x600")
    root.resizable(False, False)
    root.configure(background="#777577")

    mcont = MainContainer(root)
    mcont.pack(anchor="nw", fill="both", expand=True, pady=150)
    btog = ButtonToggles(mcont)
    btog.grid(row=0, column=0, sticky="nsew")

    root.mainloop()


main()
