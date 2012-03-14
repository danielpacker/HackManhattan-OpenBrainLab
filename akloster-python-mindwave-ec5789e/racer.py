import pygame, sys
from numpy import *
from pygame.locals import *
import scipy
from pyeeg import bin_power
pygame.init()

fpsClock= pygame.time.Clock()

window = pygame.display.set_mode((1280,720))
pygame.display.set_caption("Mindwave Viewer")

from parser import Parser

p = Parser("serial")
pb = Parser("bluetooth")

blackColor = pygame.Color(0,0,0)
redColor = pygame.Color(255,0,0)
blueColor=pygame.Color(0,0,255)
greenColor = pygame.Color(0,255,0)
whiteColor = pygame.Color(255,255,255)
deltaColor = whiteColor
thetaColor = pygame.Color(0,0,255)
alphaColor = pygame.Color(255,0,0)
betaColor = pygame.Color(0,255,00)
gammaColor = pygame.Color(0,255,255)

background_img = pygame.image.load("sdl_viewer_background.png")
#background_img = pygame.image.load("blank.png")

font = pygame.font.Font("freesansbold.ttf",20)
winfont = pygame.font.Font("freesansbold.ttf",100)
raw_eeg = True
spectra = []
iteration = 0

spectra2 = []

meditation_img = font.render("Meditation", False, redColor)
attention_img = font.render("Attention", False, redColor)

record_baseline = False

progress = 0
progress2 = 0
totaltime = 0
final_time = 0

while True:
	p.update()
	pb.update()
	window.blit(background_img,(0,0))

	if pb.sending_data:
		print("PB")
		iteration+=1
		flen = 50
			
		if len(pb.raw_values)>=500:
			spectrum, relative_spectrum = bin_power(pb.raw_values[-pb.buffer_len:], range(flen),512)
			spectra2.append(array(relative_spectrum))
			if len(spectra)>30:
				spectra2.pop(0)
				
			spectrum = mean(array(spectra2),axis=0)
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
				pygame.draw.rect(window, color, (25+i*20, 600-value*4, 5, 4*value))
		else:
			pass
		pygame.draw.circle(window,redColor, (400,200),pb.current_attention/2)
		pygame.draw.circle(window,greenColor, (400,200),60/2,1)
		pygame.draw.circle(window,greenColor, (400,200),100/2,1)
		window.blit(attention_img, (360,260))
		pygame.draw.circle(window,redColor, (300,200),pb.current_meditation/2)
		pygame.draw.circle(window,greenColor, (300,200),60/2,1)
		pygame.draw.circle(window,greenColor, (300,200),100/2,1)

		progress2 += pb.current_attention/20
		newcolor = 100 + pb.current_attention
		if (newcolor > 255): newcolor = 255
		pygame.draw.rect(window, pygame.Color(newcolor,50,50), (10+progress2, 650, 50, 50))

		totaltime += 1

		if (progress2 > 1200):
			#window.blit(winfont.render("YOU WIN", False, redColor), (200,200))
			#window.blit(winfont.render("TIME: " + str(final_time), False, redColor), (200,400))
			progress2=0
			
		
		window.blit(meditation_img, (200,260))
		if len(pb.current_vector)>7:
			m = max(pb.current_vector)
			for i in range(7):
				value = pb.current_vector[i] *100.0/m
				pygame.draw.rect(window, redColor, (200+i*30,450-value, 6,value))

		if raw_eeg:
			lv = 0
			for i,value in enumerate(pb.raw_values[-1000:]):
				v = value/ 255.0/ 5
				pygame.draw.line(window, redColor, (i+25,400-lv),(i+25, 400-v))
				lv = v
	else:
		img = font.render("Mindwave Headset is not sending data... Press F5 to autoconnect or F6 to disconnect.", False, redColor)
		window.blit(img,(100,100))

	if p.sending_data:
		print("P")
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
				pygame.draw.rect(window, color, (25+i*20, 600-value*4, 5, 4*value))
		else:
			pass
		print(p.current_attention)
		pygame.draw.circle(window,blueColor, (800,200),p.current_attention/2)
		pygame.draw.circle(window,greenColor, (800,200),60/2,1)
		pygame.draw.circle(window,greenColor, (800,200),100/2,1)
		window.blit(attention_img, (760,260))
		pygame.draw.circle(window,blueColor, (700,200),p.current_meditation/2)
		pygame.draw.circle(window,greenColor, (700,200),60/2,1)
		pygame.draw.circle(window,greenColor, (700,200),100/2,1)

		progress += p.current_attention/20
		newcolor = 100 + p.current_attention
		if (newcolor > 255): newcolor = 255
		pygame.draw.rect(window, pygame.Color(50,50, newcolor), (10+progress, 600, 50, 50))

		totaltime += 1
		if (progress == 1200):
			final_time = totaltime
		if (progress > 1200):
			#window.blit(winfont.render("YOU WIN", False, redColor), (200,200))
			#window.blit(winfont.render("TIME: " + str(final_time), False, redColor), (200,400))
			progress=0
		if (progress2 > 1200):
			#window.blit(winfont.render("YOU WIN", False, redColor), (200,200))
			#window.blit(winfont.render("TIME: " + str(final_time), False, redColor), (200,400))
			progress2=0
			
		
		window.blit(meditation_img, (600,260))
		if len(p.current_vector)>7:
			m = max(p.current_vector)
			for i in range(7):
				value = p.current_vector[i] *100.0/m
				pygame.draw.rect(window, blueColor, (600+i*30,450-value, 6,value))

		if raw_eeg:
			lv = 0
			for i,value in enumerate(p.raw_values[-1000:]):
				v = value/ 255.0/ 5
				pygame.draw.line(window, blueColor, (i+25,500-lv),(i+25, 500-v))
				lv = v
	else:
		img = font.render("Mindwave Headset is not sending data... Press F5 to autoconnect or F6 to disconnect.", False, redColor)
		window.blit(img,(100,100))


	for event in pygame.event.get():
		if event.type==QUIT:
			pygame.quit()
			sys.exit()
		if event.type==KEYDOWN:
			if event.key== K_F5:
				p.write_serial("\xc2")
			elif event.key== K_F6:
				p.write_serial("\xc1")
			elif event.key==K_ESCAPE:
				pygame.quit()
				sys.exit()
			elif event.key == K_F7:
				record_baseline = True
				p.start_raw_recording("baseline_raw.csv")
				p.start_esense_recording("baseline_esense.csv")
			elif event.key == K_F8:
				record_baseline = False
				p.stop_esense_recording()
				p.stop_raw_recording()
	pygame.display.update()
	fpsClock.tick(30)
