import pygame, sys
from numpy import *
from pygame.locals import *
import scipy
from pyeeg import bin_power
from time import sleep
from random import randint
pygame.init()

fpsClock= pygame.time.Clock()

GAME_WIDTH=1280
GAME_HEIGHT=720
mid_width = GAME_WIDTH/2
mid_height = GAME_HEIGHT/2
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT)) #, pygame.FULLSCREEN)
pygame.display.set_caption("tug-o-mind")

from parser import *

background_img = pygame.image.load("tug_bg2.png")
win_font_size = 150
win_font = pygame.font.Font("freesansbold.ttf", win_font_size)

parsers = getParsers()

# store values for each parsers
pvalues = {}

blackColor = pygame.Color(0,0,0)
redColor = pygame.Color(255,0,0)
ropeColor = pygame.Color(160, 90, 44)
blueColor=pygame.Color(0,0,255)
greenColor = pygame.Color(0,255,0)
whiteColor = pygame.Color(255,255,255)
deltaColor = whiteColor
thetaColor = pygame.Color(0,0,255)
alphaColor = pygame.Color(255,0,0)
betaColor = pygame.Color(0,255,00)
gammaColor = pygame.Color(0,255,255)


circle_size=100
rect_size=150
rope_height=10
rope_width=1100
margin=GAME_WIDTH/4
game_offset=0
game_over = False
victor = "NOBODY"
show_end = True

def resetGame():
  print("Resetting game!")
  global game_offset, victor, game_over, show_end
  game_offset = 0
  victor      = "NOBODY"
  game_over   = False
  show_end    = True
  sleep(1)
 
def sendConnect():
  for (port,parser) in parsers:
    print("Connecting to " + port)
    parser.write_serial("\xc2")
    sleep(1)
    parser.update()
    while (parser.dongle_state != "connected"):
      print(parser.dongle_state)
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
    #print(port)
    parser.update()
    #if parser.sending_data:
    #  print("port " + port)
    #  print(parser.current_meditation)
    #else:
    #  print("not sending data")

  # Draw the players
  pygame.draw.circle(window, greenColor, (circle_size+margin+game_offset, mid_height), circle_size, 0)
  pygame.draw.rect(window, redColor, (GAME_WIDTH-rect_size-margin+game_offset, mid_height-rect_size/2, rect_size, rect_size), 0)
  # draw rope between players
  space_between_shapes = GAME_WIDTH-(margin*2)-rect_size-(circle_size*2)
  pygame.draw.rect(window, ropeColor, (game_offset+(circle_size*2)+margin, mid_height-(rope_height/2), space_between_shapes, rope_height), 0)

  # the way you konw the game is over is one shape touches the middle
  # for the circle to touch the middle offset must be:
  #   half of the distance between shapes
  # for the rect to touch the middle ofset must be:
  #   minus half the distance between the sapes
  if (game_offset >= (space_between_shapes/2)):
    game_over = True
    victor = "SQUARE"
  else:
    if (game_offset <= -1*(space_between_shapes/2)):
      game_over = True
      victor = "CIRCLE"

  if (not game_over):
    randrange = 200
    randnum = random.randint(0, randrange) - randrange/2
    game_offset += randnum
    sleep(0.1)
  else:
    window.fill(redColor)
    if (show_end):
      sleep(.05)
      dark = False
      for i in range(1, 10):
        dark = not dark
        if (dark):
          screenColor = (127, 0, 0)
        else:
          screenColor = redColor
        window.fill(screenColor)
        pygame.display.update()
        sleep(.1)
        show_end = False
 
    text = win_font.render(victor + " WINS!", False, blackColor)
    #textpos = text.get_rect(center=(GAME_WIDTH/2, margin+win_font_size-(GAME_HEIGHT/2)))
    textpos = text.get_rect(center=(GAME_WIDTH/2, GAME_HEIGHT/2))
    window.blit(text, textpos)
    #window.blit(text, (GAME_WIDTH/2-textpos[0]/2, 100)) # left, top

  print("randnum: " + str(randnum))
  print("game_offset: " + str(game_offset))

  for event in pygame.event.get():
    if event.type==QUIT:
      pygame.quit()
      sys.exit()
    if event.type==KEYDOWN:
      if event.key== K_SPACE:
        resetGame()
      elif event.key== K_F5:
        sendConnect()
      elif event.key== K_F6:
        sendDisconnect()
      elif event.key==K_ESCAPE:
        closeParsers()
        pygame.quit()
        sys.exit()
  pygame.display.update()
  fpsClock.tick(30)

