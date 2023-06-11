import pynput.keyboard as KB
from gcode import Command
from session import SerialSession


SESSION = SerialSession()


class Jogger:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.z = 0

    def send(self):
        com = Command(x=self.x, y=self.y, z=self.z, f=500)
        SESSION.write(str(com))

    def xDown(self):
        self.x -= 1

    def xUp(self):
        self.x += 1

    def yDown(self):
        self.y -= 1

    def yUp(self):
        self.y += 1

    def zDown(self):
        self.z -= 1

    def zUp(self):
        self.z += 1

    def on_press(self, key):
        # use up and down arrows for y axis
        if key == KB.Key.up:
            self.yUp()
        elif key == KB.Key.down:
            self.yDown()
        # use left and right arrows for x axis
        elif key == KB.Key.left:
            self.xDown()
        elif key == KB.Key.right:
            self.xUp()
        # use + and - for z axis
        elif key == KB.Key.minus:
            self.zDown()
        elif key == KB.Key.equal:
            self.zUp()
        else:
            return
        self.send()
