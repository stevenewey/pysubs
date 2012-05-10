#!/usr/bin/env python

from PIL import Image

fontHeight = 30
fontWidth = 15

im = Image.open('sub00002.png').convert("RGB")
r, g, b = im.split()
pix = r.load()
width, height = r.size
for y in range(0, height):
    for x in range(0, width):
        if pix[x,y] < 168:
            pix[x,y] = 0
        else:
            pix[x,y] = 255

# find first horizontal row with a pixel
firstpixel = None
for y in range(0, height):
    for x in range(0, width):
        if pix[x,y] == 255:
            firstpixel = (x, y)
            break
    if firstpixel is not None:
        break
print firstpixel

# scan from first pixel height across the line
scan = []
for x in range(0,width):
    line = []
    for y in range(firstpixel[1], firstpixel[1]+fontHeight):
        line.append(pix[x,y])
    scan.append(line)

test = Image.new('RGB', (width, fontHeight))
t = test.load()
for y in range(0,fontHeight):
    for x in range(0,len(scan)):
        t[x,y] = scan[x][y]

test.save('out.png')
