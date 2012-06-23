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
ATTENTION_FACTOR = 0.1
window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("tug-o-mind")

from parser import *

background_img = pygame.image.load("bluebg.png")
win_font_size = 150
win_font = pygame.font.Font("freesansbold.ttf", win_font_size)

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
MAX_POLLS = 10
game_offset=0
game_over = False
victor = "NOBODY"
show_end = True
attention_values = ()
interactive_mode = True

# determine if we're in demo mode or using headsets
parsers = getParsers()
if (len(parsers) < 2):
  interactive_mode = False
pvalues = []


def resetGame():
  print("Resetting game!")
  global game_offset, victor, game_over, show_end
  game_offset = 0
  victor      = "NOBODY"
  game_over   = False
  show_end    = True
  interactive_mode = True
  sleep(1)
 
def sendConnect():
    global interactive_mode

    for (port,parser) in parsers:
      if (interactive_mode):
        print("Connecting to " + port)
        parser.write_serial("\xc2")
        sleep(2)
        parser.update()
        pollnum=0
        while (parser.dongle_state != "connected"):
          print(parser.dongle_state)
          parser.write_serial("\xc2")
          sleep(2)
          parser.update()
          print("polling to connect...")
          pollnum += 1
          if (pollnum >= MAX_POLLS):
            interactive_mode = False
            break
          

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
  i = 0

  if (interactive_mode):
    for (port,parser) in parsers:
      parser.update()
      if parser.sending_data:
        pvalues.append(parser.current_attention)
        print("APPENDING " + str(parser.current_attention) + " for port " + port)
      else:
        pvalues.append(0)
      #  print("not sending data")
        pass

  ############################################################################
  # DRAW GAME
  
  # draw center line
  ctr_line_width = GAME_WIDTH/40
  pygame.draw.rect(window, redColor, ((GAME_WIDTH/2)-(ctr_line_width/2), 0, ctr_line_width, GAME_HEIGHT), 0)
  #pygame.draw.rect(window, blackColor, ((GAME_WIDTH/2), 0, 1, GAME_HEIGHT), 0)

  # Draw the players
  pygame.draw.circle(window, greenColor, (circle_size+margin+game_offset, mid_height), circle_size, 0)
  pygame.draw.rect(window, blueColor, (GAME_WIDTH-rect_size-margin+game_offset, mid_height-rect_size/2, rect_size, rect_size), 0)
  # draw rope between players
  space_between_shapes = GAME_WIDTH-(margin*2)-rect_size-(circle_size*2)
  rope = pygame.Rect(game_offset+(circle_size*2)+margin, mid_height-(rope_height/2), space_between_shapes, rope_height)
  pygame.draw.rect(window, ropeColor, rope, 0)

  # the way you konw the game is over is one shape touches the middle
  # for the circle to touch the middle offset must be:
  #   half of the distance between shapes
  # for the rect to touch the middle ofset must be:
  #   minus half the distance between the sapes
  if (rope.right <= (GAME_WIDTH/2)):
    game_over = True
    victor = "CIRCLE"
  else:
    if (rope.left >= (GAME_WIDTH/2)):
      game_over = True
      victor = "SQUARE"

  if (not game_over):
    # calculate new offset
    # offset should be the difference between the attentions of the two players
    # so pvalues[port1] - pvalues[port2]
    # if 1 is greater it will be a shift right
    # if 2 is greater it will be a shift left
    if (interactive_mode):
      print("PVALUES: " + str(pvalues[0]) + " " + str(pvalues[1]))
      game_offset += int((pvalues[0] - pvalues[1]) * ATTENTION_FACTOR)
      pvalues = []
    else:
      randrange = 100
      randnum = -5 #random.randint(0, randrange) - randrange/2
      game_offset += randnum
      #print("randnum: " + str(randnum))
    # delay between updates
    sleep(0.1)
  else:
    window.fill(redColor)
    if (show_end):
      sleep(.1)
      dark = False
      for i in range(1, 7):
        dark = not dark
        if (dark):
          screenColor = (127, 0, 0)
        else:
          screenColor = redColor
        window.fill(screenColor)
        pygame.display.update()
        sleep(.075)
        show_end = False
 
    text = win_font.render(victor + " WINS!", False, blackColor)
    #textpos = text.get_rect(center=(GAME_WIDTH/2, margin+win_font_size-(GAME_HEIGHT/2)))
    textpos = text.get_rect(center=(GAME_WIDTH/2, GAME_HEIGHT/2))
    window.blit(text, textpos)
    #window.blit(text, (GAME_WIDTH/2-textpos[0]/2, 100)) # left, top

  #print("game_offset: " + str(game_offset))

  for event in pygame.event.get():
    if event.type==QUIT:
      pygame.quit()
      sys.exit()
    if event.type==KEYDOWN:
      if event.key== K_SPACE:
        resetGame()
      elif event.key== K_F5 or event.key == K_5:
        sendConnect()
      elif event.key== K_F6 or event.key == K_6:
        sendDisconnect()
      elif event.key==K_ESCAPE:
        closeParsers()
        pygame.quit()
        sys.exit()
  pygame.display.update()
  fpsClock.tick(30)

