"""
Various Utility Functions.
"""
import re
import sys
import codecs
import urllib
from copy import copy
from elementtree import ElementTree
from xml.dom import minidom


# POSIX Color Codes
ESC = chr(27)
COLOR_RED    = ESC + "[31;1m"
COLOR_YELLOW = ESC + "[33;1m"
COLOR_PURPLE = ESC + "[35;1m"
COLOR_BLUE   = ESC + "[36;1m"
COLOR_WHITE  = ESC + "[37;1m"
COLOR_RESET  = ESC + "[0m"

LOG_LEVELS = {
    'SEVERE': 0,
    'WARN': 1,
    'TITLE': 2,
    'INFO': 3,
    'FINE': 4,
    'VERBOSE': 5,
    'FINER': 6,
}


################################
#  Mozilla URL Opener
################################

class MozURLopener(urllib.FancyURLopener):
    version = 'Mozilla/4.0 (compatible)'
urllib._urlopener = MozURLopener()


################################
#  Basic Utility Functions
################################

def getHtml(url):
    """ Return the HTML for the specified URL. """
    log.finer("  Opening URL: %s" % url)
    handle = MozURLopener().open(url)
    html = handle.read()
    handle.close()
    return html


def downloadFile(url, filePath):
    """ Download the specified URL to the local filePath. """
    log.finer("  Opening URL: %s to %s" % (url, filePath))
    MozURLopener().retrieve(url, filePath)


def replaceChars(inStr, chars):
    """ Remove the invalid chars from the specified string. """
    newStr = inStr
    for char, newChar in chars.iteritems():
        newStr = newStr.replace(char, newChar)
    return newStr


def removeChars(inStr, chars):
    """ Remove the invalid chars from the specified string. """
    newStr = inStr
    for char in chars:
        newStr = newStr.replace(char, "")
    return newStr

def removeExtraChars(inStr, char):
    """ Remove duplicate chars in the string. Only works up to 5 repeats. """
    for i in range(5):
        inStr = inStr.replace(char+char, char)
    return inStr

def keepChars(inStr, chars):
    """ Only Keep the basic a-zA-Z0-9 chars. """
    newStr = ""
    for char in instr:
        if (char in SEARCH_CHARS):
            newStr += char
    return newStr.strip()

def removePrefixWords(str, words):
    """ Remove Stop words from the beginning of the specified string. """
    newStr = str
    for stopWord in words:
        stopWord = "%s " % stopWord
        if (newStr.lower().startswith(stopWord)):
            newStr = newStr[len(stopWord):]
            break
    return newStr

def promptUser(choices, choiceStr, question=None, maxToShow=20):
    """ Get a response from the user.
        @param choices:     List of choices to display
        @param choiceStr:   Function to display the choice string
        @param question:    Question to ask the user
    """
    # Display choices to the user
    print ""
    validinput = ['']
    for i in range(len(choices)):
        validinput.append(str(i+1))
        try:
            try: print encode("  %2s. %s" % (i+1, choiceStr(choices[i])))
            except: print "  %2s. %s" % (i+1, choiceStr(choices[i]))
        except:
            pass
        if (i == maxToShow-1): break
    # Get a response from the user
    response = "<UNANSWERED>"
    question = question or "  Please select the correct item"
    question = "%s (0 for None) [0]: " % question
    while (response not in validinput):
        response = raw_input("\n%s" % question)
        if (response not in validinput):
            print "  Invalid input, please choose one of: %s" % validinput
    # We have a response, return the correct choice
    if (response == ''):
        print "  You selected: None"
        return None
    selection = choices[int(response)-1]
    print "  You selected: %s" % choiceStr(selection)
    return selection


################################
#  ElementTree Helpers
################################

def encode(inStr):
    """ Encode the specifiec string to the system setting.
        IMDBPY Ref: http://imdbpy.sourceforge.net/docs/README.utf8.txt
        Python Ref: http://docs.python.org/library/codecs.html
    """
    if (isinstance(inStr, basestring)):
        return inStr.encode(sys.stdout.encoding, 'xmlcharrefreplace')
    return inStr


def escape(text):
    """ Escapse special XML entities. """
    if (isinstance(text, basestring)):
        try: text = encode(text)
        except: text = copy(text)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
    return text


################################
#  Generic Logger Class
################################

class Logger:
    """ Generic Logger Class """
    def __init__(self):
        self.level = 3
            
    def _print(self, message, level, color):
        """ Log the message to stdout. """
        if (self.level >= level):
            sys.stdout.write(color)
            try: sys.stdout.write("%s\n" % message)
            except: sys.stdout.write(encode("%s\n" % message))
            sys.stdout.write(COLOR_RESET)
            sys.stdout.flush()
            return message
    
    def severe(self, message):   return self._print(message, LOG_LEVELS['SEVERE'],  COLOR_RED)
    def warn(self, message):     return self._print(message, LOG_LEVELS['WARN'],    COLOR_YELLOW)
    def title(self, message):    return self._print(message, LOG_LEVELS['TITLE'],   COLOR_BLUE)
    def info(self, message):     return self._print(message, LOG_LEVELS['INFO'],    COLOR_RESET)
    def fine(self, message):     return self._print(message, LOG_LEVELS['FINE'],    COLOR_RESET)
    def verbose(self, message):  return self._print(message, LOG_LEVELS['VERBOSE'], COLOR_PURPLE)
    def finer(self, message):    return self._print(message, LOG_LEVELS['FINER'],   COLOR_RESET)

# Create the Singleton Logger
global log
if (not globals().get('log')):
    log = Logger()
    
