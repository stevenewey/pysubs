#!/usr/bin/env python

import sys, os
from pickle import load, dump
from PIL import Image
from operator import itemgetter

FONT_HEIGHT = 30
DEFAULT_FONT_DB = os.path.join(os.path.split(__file__)[0], 'tiresias.db')
FLATTEN_THRESHOLD = 168
SPACE_PIXELS = 6
DEFAULT_SENSITIVITY = 25

class SubtitleToText(object):
    
    store = {}
    pixelData = None
    sourceWidth = None
    sourceHeight = None
    linesData = None
    stats = {
        'exactMatch' : 0,
        'linesMatch' : 0,
    }
    
    def __init__(self, db=DEFAULT_FONT_DB, fontHeight=FONT_HEIGHT):
        self.dbFile = db
        self.fontHeight = fontHeight
        try:
            self.loadDb()
        except:
            pass
    
    def loadDb(self):
        dbPtr = open(self.dbFile, 'r')
        self.store = load(dbPtr)
        dbPtr.close()
    
    def saveDb(self):
        dbPtr = open(self.dbFile, 'w')
        dump(self.store, dbPtr)
        dbPtr.close()
    
    def parseImage(self, sourceImage, optimism=False):
        output = ''
        self.readImage(sourceImage)
        self.getLines()
        for line in self.linesData:
            lineOut = ''
            for character in line:
                if len(character) > 0:
                    findMatch = self.findCharacter(character, optimism=optimism)
                    if findMatch is None:
                        lineOut += '_'
                    else:
                        lineOut += findMatch
                else:
                    lineOut += ' '
            output += lineOut.lstrip() + '\n'
        return output
    
    def readImage(self, sourceImage):
        # load green layer of image
        bitmap = Image.open(sourceImage).convert("RGB").split()[1]
        self.pixelData = bitmap.load()
        self.sourceWidth, self.sourceHeight = bitmap.size
    
    def getLine(self, startLine, flattenThreshold, spacePixels):
        firstPixelLine = None
        characters = []
        character = []
        spaces = 0
        # find the first line with a pixel
        for y in range(startLine, self.sourceHeight):
            for x in range(0, self.sourceWidth):
                # flatten pixel data to a binary state
                if self.pixelData[x,y] < flattenThreshold:
                    self.pixelData[x,y] = 0
                else:
                    self.pixelData[x,y] = 1
                # look for a pixel
                if self.pixelData[x,y] == 1:
                    firstPixelLine = y
                    break
            if firstPixelLine is not None:
                break
        # scan the resultant line for characters
        if firstPixelLine is not None:
            for x in range(0, self.sourceWidth):
                line = []
                for y in range(firstPixelLine, firstPixelLine+self.fontHeight):
                    # flatten pixel data to a binary state
                    if self.pixelData[x,y] < flattenThreshold:
                        self.pixelData[x,y] = 0
                    else:
                        self.pixelData[x,y] = 1
                    line.append(self.pixelData[x,y])
                if sum(line) == 0:
                    # add a pixel to the spacer info
                    spaces += 1
                if len(character) > 0 and sum(line) == 0:
                    # if we've reached the end of the character (no more line data) add it to the list and reset
                    character = self.realign(character)
                    characters.append(character)
                    character = []
                    spaces = 0
                if spaces > spacePixels and len(character) > 0:
                    # if there's more than X spacer pixels and we've started a new character, that was a space
                    characters.append([])
                    spaces = 0
                if sum(line) > 0:
                    # append this line to the character
                    character.append(line)
            if firstPixelLine is None:
                firstPixelLine = 0
            return characters, firstPixelLine+self.fontHeight+1
    
    def getLines(self, flattenThreshold=FLATTEN_THRESHOLD, spacePixels=SPACE_PIXELS):
        nextLine = 0
        lines = []
        while 1:
            lineinfo = self.getLine(nextLine, flattenThreshold, spacePixels)
            if lineinfo is not None:
                if len(lineinfo[0]) > 0:
                    lines.append(lineinfo[0])
                nextLine = lineinfo[1]
            else:
                break
        self.linesData = lines
    
    def renderToAscii(self, line=None, character=None):
        if line is not None and line <= len(self.linesData):
            start = line
            end = line + 1
        else:
            start = 0
            end = len(self.linesData)
        row = ''
        for i in range(start, end):
            if character is not None and character <= len(self.linesData[i]):
                chstart = character
                chend = character + 1
            else:
                chstart = 0
                chend = len(self.linesData[i])
            for y in range(0, self.fontHeight):
                for character in range(chstart,chend):
                    if len(self.linesData[i][character]) > 0:
                        for x in range(0, len(self.linesData[i][character])):
                            if self.linesData[i][character][x][y] == 0:
                                row += ' '
                            else:
                                row += '*'
                        row += '  '
                    else:
                        row += '          '
                row += '\n'
        return row
    
    def renderCharToAscii(self, character):
        row = ''
        if len(character) > 0:
            for y in range(0, len(character[0])):
                for x in range(0, len(character)):
                    if character[x][y] == 0:
                        row += ' '
                    else:
                        row += '*'
                row += '\n'
        return row
    
    def buildDb(self):
        output = ''
        for line in self.linesData:
            for character in line:
                if len(character) > 0:
                    findMatch = self.findCharacter(character, training=True)
                    if findMatch is None:
                        print self.renderCharToAscii(character)
                        userchar = raw_input("What is it? ")
                        if userchar != '':
                            if not self.store.has_key(userchar):
                                self.store[userchar] = []
                            self.store[userchar].append([character, 0, 0])
                            output += userchar
                    else:
                        output += findMatch
                else:
                    output += ' '
            output += '\n'
        return output
    
    def buildDbFromDir(self, directory='.', delete=False):
        files = []
        output = ''
        for entry in os.listdir(directory):
            files.append(entry)
        files.sort()
        for entry in files:
            if entry[-4:] == '.png':
                print entry
                self.readImage(os.path.join(directory, entry))
                self.getLines()
                sentence = self.buildDb()
                output += sentence
                print sentence
                if delete is True:
                    os.remove(os.path.join(directory, entry))
        print output
    
    def parseImagesFromDir(self, directory='.', delete=False, optimism=False):
        files = []
        output = ''
        for entry in os.listdir(directory):
            files.append(entry)
        files.sort()
        for entry in files:
            if entry[-4:] == '.png':
                sentence = self.parseImage(os.path.join(directory, entry), optimism=optimism)
                output += sentence
                print sentence
                if delete is True:
                    os.remove(os.path.join(directory, entry))
        return output
    
    def findCharacter(self, character, training=False, optimism=False):
        for key in self.store:
            # easiest first, is it an exact match?
            for pattern in self.store[key]:
                if pattern[0] == character:
                    self.stats['exactMatch'] += 1
                    return key
        # compare grid
        search = self.compareLines(character, training=training, optimism=optimism)
        if search is not None:
            self.stats['linesMatch'] += 1
            return search
        # didn't find anything :(
        return None
    
    def compareLines(self, character, training=False, optimism=False, sensitivity=DEFAULT_SENSITIVITY):
        near = {}
        # line-by-line analysis
        aX = self.lineValuesX(character)
        aY = self.lineValuesY(character)
        for key in self.store:
            for i in range(0, len(self.store[key])):
                dbChar = self.store[key][i][0]
                diffX = []
                diffY = []
                if self.store[key][i][1] == 0:
                    # cache line averages for DB characters
                    self.store[key][i][1] = self.lineValuesX(dbChar)
                    self.store[key][i][2] = self.lineValuesY(dbChar)
                bX = self.store[key][i][1]
                bY = self.store[key][i][2]
                if abs(len(aX)-len(bX)) > 4:
                    # if the width of the character varies too much, ignore
                    continue
                for index in range(0, len(aX)):
                    if index < len(bX):
                        diffX.append(abs(aX[index]-bX[index]))
                    else:
                        diffX.append(aX[index])
                for index in range(0, len(aY)):
                    if index < len(bY):
                        diffY.append(abs(aY[index]-bY[index]))
                    else:
                        diffY.append(aY[index])
                near[key+' '+str(i)] = (sum(diffX) + sum(diffY)) / 2
        near = sorted(near.iteritems(), key=itemgetter(1))
        if len(near) > 0:
            if near[0][1] < sensitivity or optimism is True:
                return near[0][0].split(' ')[0]
        if len(near) > 0 and training is True:
            print near
        return None
    
    def realign(self, character):
        """ Realign character to top and left """
        xchar = None
        ychar = None
        for x in range(0, len(character)):
            for y in range(0, len(character[x])):
                if (xchar is None or x < xchar) and character[x][y] == 1:
                    xchar = x
                if (ychar is None or y < ychar) and character[x][y] == 1:
                    ychar = y
        # recreate character
        newChar = [0] * len(character)
        for x in range(0, len(newChar)):
            newChar[x] = [0] * len(character[x])
        for x in range(xchar, len(character)):
            for y in range(ychar, len(character[x])):
                if character[x][y] == 1:
                    newChar[x-xchar][y-ychar] = 1
        return newChar
    
    def lineValuesX(self, character):
        lineTotals = []
        for x in range(0, len(character)):
            lineTotal = []
            for y in range(0, len(character[x])):
                if character[x][y] == 1:
                    lineTotal.append(y+1)
            lineTotals.append(sum(lineTotal))
        return lineTotals
    
    def lineValuesY(self, character):
        """ Rotate character 90 degrees """
        newChar = [0] * len(character[0])
        for y in range(0, len(character[0])):
            newChar[y] = [0] * len(character)
            for x in range(0, len(character)):
                newChar[y][x] = character[x][y]
        return self.lineValuesX(newChar)
    