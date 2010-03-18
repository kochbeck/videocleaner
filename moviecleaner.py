#!/usr/bin/env python
# encoding: utf-8
"""
Rename video files to match XBMC, Boxee, Plex formats.

  Basic Usage
  -----------
  This program will first look for an nfo file on disk and use any title,
  year, country information it can gather from that file. If an NFO file does
  not exist, or the NFO does not appear to be valid, it will search IMDB.
  
  Searching IMDB is done by first looking at the nfo file again (valid or
  invalid) and look for a proper link to IMDB.  If one is found, it will use
  that url to pull IMDB imformation. If a link is not found or the NFO file
  does not exist, it will search IMDB for the title and year gathered from
  the directory name.
  
  Once IMDB information is gathered, if the --savenfo file option is
  specified, it will be saved to disk.  The next time this program runs that
  information will be found, and will not need to look up the information
  from IMDB again.  You can however delete the nfo file to start the process
  over again.
  
  Saving an nfo, renaming directories and renaming files all require a valid
  nfo to exist or a successful lookup of IMDB information or the actions will
  not be performed.
  
  Looking up Trailers
  -------------------
  Looking up trailers and downloading trailers can be done in one step or
  two.  If you lookup the trailer without downloading it, the trailer url
  will be saved to the nfo file so that it can be downloaded at a later time
  without the need for human intervention.  This is done because downloading
  many trailers can often take a while to complete, and it doesn't make sense
  to have the user sit through that whole process.
  
  Displaying Lists
  ----------------
  When displaying a list, looking up IMDB or trailer information will be
  bypassed.
"""
import os
import sys
from util import log
from util import LOG_LEVELS
from movie import Movie
from optparse import OptionGroup
from optparse import OptionParser
from optparse import IndentedHelpFormatter
verbose = LOG_LEVELS['VERBOSE']


#################################
#  Renamer Object
#################################
        
class MovieCleaner:
    """ Rename video files to match XBMC, Boxee, Plex formats. """
    
    def __init__(self, opts):
        log.level = LOG_LEVELS[opts.log]
        if (opts.verbose): log.level = LOG_LEVELS['FINER']
        # Runtime Settings
        self.baseDir         = opts.basedir.rstrip('/')   # Base directory to search for files
        self.single          = opts.single.rstrip('/')    # DirName when processing Single Dir
        self.startAt         = opts.startat               # Start at the specified Dir
        self.list            = opts.list                  # Display a list
        self.print0          = opts.print0                # Delimit list items by NULL
        # Runtime Settings
        self.foreign         = opts.aka                   # Use AKA for DirName and FileName
        self.lookupTrailer   = opts.trailer               # Lookup trailer page
        self.logImdb         = opts.imdbinfo              # Display IMDB Information
        # Actions to Perform
        self.forceUpdate     = opts.force                 # Force IMDB Update (even if valid NFO exists)
        self.renameDir       = opts.renamedir             # Old Directory Path on Disk
        self.renameFiles     = opts.renamefiles           # Rename files or not
        self.saveNfo         = opts.savenfo               # Create NFO Files
        self.downloadTrailer = opts.download              # Download trailer
    
    def run(self):
        """ Loop to search and rename all movie files. """
        if (self.list):      return self._processListRequest()
        elif (self.single):  return self._processSingleRequest()
        else:                return self._processCompleteDirectory()
        
    def _processListRequest(self):
        """ Process a list Request. """
        log.level = -1
        listItems = []
        for dirName in sorted(os.listdir(self.baseDir)):
            if (os.path.isdir(dirName)):
                dirPath = "%s/%s" % (self.baseDir, dirName)
                movie = Movie(dirPath)
                if   (self.list == 'novideo'): listItems += movie.getNoVideoList()
                elif (self.list == 'badnfo'):  listItems += movie.getBadNfoList()
                elif (self.list == 'nonfo'):   listItems += movie.getMissingNfoList()
                elif (self.list == 'hassub'):  listItems += movie.getHasSubtitleList()
                elif (self.list == 'nosub'):   listItems += movie.getNoSubtitleList()
                elif (self.list == 'suberr'):  listItems += movie.getSubtitleErrorList()
        # Print the Result
        if (listItems) and (self.print0):
            sys.stdout.write("\0".join(listItems))
        elif (listItems):
            print "\n".join(listItems)
    
    def _processSingleRequest(self):
        """ Process a single directory in baseDir. """
        for dirName in sorted(os.listdir(self.baseDir)):
            if (os.path.isdir(dirName)) and (self.single.lower() in dirName.lower()):
                dirPath = "%s/%s" % (self.baseDir, dirName)
                self._processMovieDirectory(dirPath)
                break
    
    def _processCompleteDirectory(self):
        """ Process every movie directory in baseDir. """
        for dirName in sorted(os.listdir(self.baseDir)):
            if (os.path.isdir(dirName)):
                if (not self.startAt) or (self.startAt.lower() in dirName.lower()):
                    dirPath = "%s/%s" % (self.baseDir, dirName)
                    self._processMovieDirectory(dirPath)
                    self.startAt = None
            
    def _processMovieDirectory(self, dirPath):
        """ Process the specfied directory path. """
        # Only ping the web for info if we need it
        movie = Movie(dirPath)
        movie.fetchVideoInfo(self.forceUpdate, self.foreign)
        # Perform the Actions
        if (self.lookupTrailer):      movie.lookupTrailerUrl(self.foreign)
        if (log.level >= verbose):    movie.logClassVars()
        if (self.logImdb):            movie.logImdbVars()
        if (self.saveNfo):            movie.saveNfo(self.foreign)
        if (self.renameFiles):        movie.renameFiles()
        if (self.renameDir):          movie.renameDirectory()
        if (self.downloadTrailer):    movie.downloadTrailer()

        
#################################
#  Option Formatter
#################################  

class HelpFormatter(IndentedHelpFormatter):
    def __init__(self):
        IndentedHelpFormatter.__init__(self)
        self.max_help_position = 50
        self.width = 120
        
    def format_description(self, description):
        return "  " + description.strip() + "\n"
        
        
#################################
#  Command Line Interface
#################################

if (__name__ == "__main__"):
    try:
        # Build the OptionParser
        desc = sys.modules['__main__'].__doc__
        version = "%prog version 10.01"
        parser = OptionParser(description=desc, formatter=HelpFormatter(), version=version)
        parser.add_option("-b", "--basedir",   help="Base directory to search for files", default=".")
        parser.add_option("-s", "--single",    help="Only process single movie", default="")
        parser.add_option(      "--startat",   help="Start at the specified Dir match")
        parser.add_option("-l", "--log",       help="Log level: INFO, FINE, VERBOSE, FINER", default='INFO')
        parser.add_option("-v", "--verbose",   help="Same as setting --log=FINER", action='store_true', default=False)
        # List Options
        lists = OptionGroup(parser, "Display Listing")
        lists.add_option("--list",             help="Display List: novideo, badnfo, nonfo, hassub, nosub, suberr")
        lists.add_option("-0", "--print0",     help="Delimit items by NULL (for xargs)", action='store_true', default=False)
        parser.add_option_group(lists)
        # Runtime Settings
        runtime = OptionGroup(parser, "Runtime Options")
        runtime.add_option("-a", "--aka",      help="Use AKA title (for foreign films)", action='store_true', default=False)
        runtime.add_option("-f", "--force",    help="Force IMDB update even if a valid NFO file exists", action='store_true', default=False)
        runtime.add_option("-t", "--trailer",  help="Lookup trailer page from TrailerAddict", action='store_true', default=False)
        runtime.add_option("-i", "--imdbinfo", help="Display raw IMDB information", action='store_true', default=False)
        parser.add_option_group(runtime)
        # Actions to Perform
        actions = OptionGroup(parser, "Actions to Perform")
        actions.add_option("--renamedir",      help="Rename containing directories to IMDB title", action='store_true', default=False)
        actions.add_option("--renamefiles",    help="Rename video files to IMDB title", action='store_true', default=False)
        actions.add_option("--savenfo",        help="Create NFO file containing IMDB info", action='store_true', default=False)
        actions.add_option("--download",       help="Download trailer from TrailerAddict", action='store_true', default=False)
        parser.add_option_group(actions)
        # OK, Lets Get Going
        options, args = parser.parse_args()
        MovieCleaner(options).run()
    except KeyboardInterrupt:
        log.severe("\nKeyboard Interrupt: quitting.")
    
    
