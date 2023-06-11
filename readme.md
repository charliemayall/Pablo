
# Pablo - CNC Painting Robot

![Architecture](https://github.com/charliemayall28/Pablo/blob/f071e4163d11fea55131712ccda472d6e853b10b/assets/arch.png)


## Overview
Pablo is a painting robot that my group and I produced for our end-of-year project for the MET2A course, Cambridge University.

My role was to design and implement the software that enabled the stream of data from the app to be converted into GCode to control the robot.

## The software
In short, the code in this repository does the following:
- Opens a websocket connection on a Raspberry Pi.
- Receives data from the AWS server that the IOS app sends to.
- Adds the data to a queue, waiting for the robot to be ready.
- Extracts the position and color data to a usable format.
- Performs checks to avoid out-of-bounds movements.
- Adds additional GCode to the stream to perform processes such as refilling the brush.
- Optionally, alters the user's strokes to change painting style, and to optimise the painting process.
- Writes the GCode through a serial connection to GRBL on the Arduino.


![Pablo](https://github.com/charliemayall28/Pablo/blob/f071e4163d11fea55131712ccda472d6e853b10b/assets/pablo-full.jpeg)
![Pablo](https://github.com/charliemayall28/Pablo/blob/f071e4163d11fea55131712ccda472d6e853b10b/assets/pablo-pic.jpeg)