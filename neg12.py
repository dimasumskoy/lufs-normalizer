#!/usr/bin/python
import os
import sys
import re
import subprocess
import mimetypes

LUFS_VALUE = -12

def r128Stats(filePath):
    """ takes a path to an audio file, returns a dict with the loudness
    stats computed by the ffmpeg ebur128 filter """
    ffargs = ['ffmpeg',
              '-nostats',
              '-i',
              filePath,
              '-filter_complex',
              'ebur128',
              '-f',
              'null',
              '-']
    try:
        proc = subprocess.Popen(ffargs, stderr=subprocess.PIPE)
        stats = proc.communicate()[1]
        summaryIndex = stats.rfind('Summary:')
        summaryList = stats[summaryIndex:].split()
        ILufs = float(summaryList[summaryList.index('I:') + 1])
        IThresh = float(summaryList[summaryList.index('I:') + 4])
        LRA = float(summaryList[summaryList.index('LRA:') + 1])
        LRAThresh = float(summaryList[summaryList.index('LRA:') + 4])
        LRALow = float(summaryList[summaryList.index('low:') + 1])
        LRAHigh = float(summaryList[summaryList.index('high:') + 1])
        statsDict = {'I': ILufs, 'I Threshold': IThresh, 'LRA': LRA,
                     'LRA Threshold': LRAThresh, 'LRA Low': LRALow,
                     'LRA High': LRAHigh}
    except:
        return False
    return statsDict


def linearGain(iLUFS, goalLUFS=LUFS_VALUE):
    """ takes a floating point value for iLUFS, returns the necessary
    multiplier for audio gain to get to the goalLUFS value """
    gainLog = -(iLUFS - goalLUFS)
    return 10 ** (gainLog / 20)


def ffApplyGain(inPath, outPath, linearAmount):
    """ creates a file from inpath at outpath, applying a filter
    for audio volume, multiplying by linearAmount """
    ffargs = ['ffmpeg', '-y', '-i', inPath,
              '-af', 'volume=' + str(linearAmount)]
    if outPath[-4:].lower() == '.mp3':
        ffargs += ['-acodec', 'libmp3lame', '-ab', '320k']
    ffargs += [outPath]
    try:
        subprocess.Popen(ffargs, stderr=subprocess.PIPE)
    except:
        return False
    return True


def notAudio(filePath):
    if os.path.basename(filePath).startswith("audio"):
        return True
    thisMime = mimetypes.guess_type(re.escape(filePath))[0]
    if thisMime is None or not thisMime.startswith("audio"):
        return True
    return False


def neg23Directory(directoryPath):
    fileList = os.listdir(directoryPath)
    for thisFile in fileList:
        thisPath = os.path.join(directoryPath, thisFile)
        if notAudio(thisPath):
            continue
        neg23File(thisPath)
    print "Batch complete."


def neg23File(filePath):
    if notAudio(filePath):
        print "Not a valid audio file."
        return False
    print "Scanning " + filePath + " for loudness..."
    loudnessStats = r128Stats(filePath)
    if not loudnessStats:
        print "neg12 encountered an error scanning " + filePath
        return
    gainAmount = linearGain(loudnessStats['I'])
    outputDir = os.path.join(os.path.dirname(filePath), "neg12")
    if not os.path.isdir(outputDir):
        os.makedirs(outputDir)
    outputPath = os.path.join(outputDir, os.path.basename(filePath))
    print "Creating -12LUFS file at " + outputPath
    ffGainSuccess = ffApplyGain(filePath, outputPath, gainAmount)
    if not ffGainSuccess:
        print "neg12 encountered an error applying gain to " + filePath
        return
    print "Done"


if __name__ == "__main__":
    if len(sys.argv) == 2 and os.path.isdir(sys.argv[1]):
        neg23Directory(sys.argv[1])
    elif len(sys.argv) == 2 and os.path.isfile(sys.argv[1]):
        neg23File(sys.argv[1])
    elif len(sys.argv) == 2 and os.path.isfile(os.path.join(os.getcwd(),
                                                            sys.argv[1])):
        neg23File(os.path.join(os.getcwd(), sys.argv[1]))
    else:
        correctUsage = "Please provide a single file or directory.\n"
        correctUsage += "Correct usage: neg12 somefile.wav OR "
        correctUsage += "neg12 /directory/for/batch/processing/"
        print correctUsage
