import pygame, sys
from numpy import *
from pygame.locals import *
import scipy
from pyeeg import bin_power
from time import sleep
pygame.init()

fpsClock= pygame.time.Clock()

window = pygame.display.set_mode((1280,720))
pygame.display.set_caption("Mindwave Viewer")

from parser import *

background_img = pygame.image.load("sdl_viewer_background.png")

parsers = getParsers()

# store values for each parsers
pvalues = {}


def sendConnect():
  for (port,parser) in parsers:
    print("Connecting to " + port)
    parser.write_serial("\xc2")
    sleep(1)
    parser.update()
    while (parser.dongle_state != "connected"):
      print(parser.dongle_state)
      #parser.write_serial("\xc1")
      parser.write_serial("\xc2")
      sleep(1)
      parser.update()
      print("polling to connect...")

def sendDisconnect():
  for (port,parser) in parsers:
    print("Disconnecting " + port)
    parser.write_serial("\xc1")
    sleep(0.5)

def closeParsers():
  for (port,parser) in parsers:
    parser.socket.close()

while True:
  window.blit(background_img,(0,0))
  for (port,parser) in parsers:
    print(port)
    parser.update()
    if parser.sending_data:
      print("port " + port)
      print(parser.current_meditation)
    else:
      print("not sending data")

  for event in pygame.event.get():
    if event.type==QUIT:
      pygame.quit()
      sys.exit()
    if event.type==KEYDOWN:
      if event.key== K_F5:
        sendConnect()
      elif event.key== K_F6:
        sendDisconnect()
      elif event.key==K_ESCAPE:
        closeParsers()
        pygame.quit()
        sys.exit()
  pygame.display.update()
  fpsClock.tick(30)

