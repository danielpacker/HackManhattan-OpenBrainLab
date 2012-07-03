import pygame, sys
from numpy import *
from pygame.locals import *
import scipy
from pyeeg import bin_power
pygame.init()
import serial
from time import sleep

MAX_POLLS = 55
fpsClock= pygame.time.Clock()

window = pygame.display.set_mode((1024,600))
pygame.display.set_caption("Mindwave Viewer")

from parser import *

def sendConnect():
    for (port,parser) in parsers:
      print("Connecting to " + port)
      parser.write_serial("\xc2")
      sleep(1)
      parser.update()
      pollnum=0
      while (parser.dongle_state != "connected"):
        print(parser.dongle_state)
        parser.write_serial("\xc2")
        sleep(1)
        parser.update()
        print("polling to connect...")
        pollnum += 1
        if (pollnum >= MAX_POLLS):
          break
          

def sendDisconnect():
  for (port,parser) in parsers:
    print("Disconnecting " + port)
    parser.write_serial("\xc1")
    sleep(0.5)

def closeParsers():
  for (port,parser) in parsers:
    parser.socket.close()

# scan for 2 attached Mindwave dongles
parsers = getParsers()
if (len(parsers) < 2):
  print "Please connect two Mindwave dongles"
  closeParsers()
  pygame.quit()
  sys.exit()
pvalues = []

# scan for available arduino ports.
arduinoPort = []
for pNum in range(256):
  pName = "/dev/ttyACM"+str(pNum)
  try:
    s = serial.Serial(pName)
    arduinoPort.append(pName)
    s.close()
  except serial.SerialException:
    pass

arduino = serial.Serial(arduinoPort[0],9600)


blackColor = pygame.Color(0,0,0)
redColor = pygame.Color(255,0,0)
greenColor = pygame.Color(0,255,0)
deltaColor = pygame.Color(100,0,0)
thetaColor = pygame.Color(0,0,255)
alphaColor = pygame.Color(255,0,0)
betaColor = pygame.Color(0,255,00)
gammaColor = pygame.Color(0,255,255)

background_img = pygame.image.load("sdl_viewer_background.png")


font = pygame.font.Font("freesansbold.ttf",21)
raw_eeg = True
spectra = []
iteration = 0
null = 0 
serialcounter = 0
serialdelay = 5

meditation_img = font.render("Meditation", False, redColor)
attention_img = font.render("Attention", False, redColor)
signal_img = font.render("Contact Quality ", False, redColor)
key_img = font.render("d   t   a   a   b   b   g   g", False, redColor) 

record_baseline = False


while True:
        for (port,parser) in parsers:
          parser.update()
          if parser.sending_data:
            pvalues.append(parser.current_attention)
            print("APPENDING " + str(parser.current_attention) + " for port " + port)
          else:
            pvalues.append(0)         
            print("not sending data")   
            pass   
        arduino.write(str(pvalues[0]/10))
        arduino.write(str(pvalues[1]/10))
        print (pvalues[0]/10)," ",(pvalues[1]/10)
        pvalues = []
        

        window.blit(background_img,(0,0))

        for (port,parser) in parsers:
          p = parser
          if p.sending_data:
                iteration+=1
                flen = 50
                        
                if len(p.raw_values)>=500:
                       spectrum, relative_spectrum = bin_power(p.raw_values[-p.buffer_len:], range(flen),512)
                       spectra.append(array(relative_spectrum))
                       if len(spectra)>30:
                                spectra.pop(0)
                                
                       spectrum = mean(array(spectra),axis=0)
                       for i in range (flen-1):
                                value = float(spectrum[i]*1000) 
                                if i<3:
                                        color = deltaColor
                                elif i<8:
                                        color = thetaColor
                                elif i<13:
                                        color = alphaColor
                                elif i<30:
                                        color = betaColor
                                else:
                                        color = gammaColor
                                pygame.draw.rect(window, color, (25+i*10,200-value, 5,value))
                else:
                        pass
                pygame.draw.circle(window,redColor, (810,150),p.current_attention/2)
                pygame.draw.circle(window,greenColor, (810,150),60/2,1)
                pygame.draw.circle(window,greenColor, (810,150),100/2,1)
                window.blit(attention_img, (760,210))
                pygame.draw.circle(window,redColor, (650,150),p.current_meditation/2)
                pygame.draw.circle(window,greenColor, (650,150),60/2,1)
                pygame.draw.circle(window,greenColor, (650,150),100/2,1)
                window.blit(meditation_img, (600,210))

                serialcounter += 1

                if (p.poor_signal < 50 and serialcounter > serialdelay):
                        pygame.draw.circle(window, greenColor, (150,400),60/2)
                        serialcounter = 0

                elif serialcounter > serialdelay: 
			pygame.draw.circle(window, redColor, (150,400),60/2)
			serialcounter = 0
 
     

                window.blit(signal_img, (100,325))
                     

                if len(p.current_vector)>7:
                        m = max(p.current_vector)
                        if m == 0:
                                m = 0.01
                        for i in range(8):
                                value = p.current_vector[i] *100.0/m
                                pygame.draw.rect(window, redColor, (600+i*30,450-value, 6,value))

                window.blit(key_img, (600, 275))

                if raw_eeg:
                        lv = 0
                        for i,value in enumerate(p.raw_values[-1000:]):
                                v = value/ 255.0/ 5
                                pygame.draw.line(window, redColor, (i+25,500-lv),(i+25, 500-v))
                                lv = v
        else:
                img = font.render("Mindwave Headset is not sending data... Press F5 to autoconnect or F6 to disconnect.", False, redColor)
                window.blit(img,(100,100))
        
        for event in pygame.event.get():
                if event.type==QUIT:
                        closeParsers()
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
