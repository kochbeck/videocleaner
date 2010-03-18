"""
Movie Object.
Stores and manipulates a movie on disk.

IMDB Info Contains:
  ['writer', u'distributors', 'sound mix', 'genres', 'runtimes', 'director',
   'miscellaneous companies', 'cinematographer', u'thanks', 'year', 'sound crew', 'color info',
   'languages', 'plot', 'kind', 'producer', 'title', 'assistant director', 'plot outline',
   'aspect ratio', 'visual effects', 'cast', 'editor', 'certificates', 'original music',
   'cover url', 'canonical title', 'long imdb title', 'long imdb canonical title']
   
"""
import os
import re
import time
import util
import imdb
import htmlentitydefs
from elementtree import ElementTree
from parsers import traileraddict
from parsers import youtube
from util import log
from video import Video
imdbpy = imdb.IMDb()

# Other Defined Constants
TRAILER_STRING   = '-trailer.'                             # String to catch samples
IMDB_REGEX       = r'http://www.imdb.com/title/tt(\d+?)/'  # IMDB Regex to get MovieID
IMDB_MAX_RESULTS = 10                                      # Max Results to show from IMDB
NFO_BASE_ATTR    = 'movie'                                 # Base Attr for Movie NFOs
NFO_REQ_ATTRS    = ['title', 'year', 'country']            # Required Attrs for valid NFO


class Movie(Video):
    """ Represents a movie on Disk. """
    
    def __init__(self, dirPath):
        Video.__init__(self, dirPath)                   # Call parent contructor
        self.curTrailerName = self._getTrailerFile()    # Current Trailer FileName
        self.imdbUrl        = None                      # URL to IMDB Info
        self.imdbInfo       = None                      # IMDB information
        self.imdbUpdate     = None                      # Date we last searched IMDB
        self.trailerUrl     = None                      # New TrailerAddict URL
        self._newInfoFound  = False                     # Set True when New Info is Found
        
    def __str__(self):
        title = self.title or self.curTitle
        year = self.year or self.curYear
        return "<Movie: %s (%s)>" % (title, year)
        
    def logClassVars(self):
        """ Log class variables to stdout. """
        attrs = ['dirPath', 'curDirName', 'curFileNames', 'curNfoName', 'videoTags',
            'subtitles', 'title', 'year', 'country', 'aka', 'trailerUrl', 'newDirName',
            'newFileNames', 'newFilePrefix']
        for attr in attrs:
            log.verbose("  self.%s = %s" % (attr, getattr(self, attr)))
        
    def logImdbVars(self):
        """ Log IMDB variables to stdout. """
        if (not self.imdbInfo):
            log.info("  No IMDB information.")
        for key in sorted(self.imdbInfo.keys()):
            log.verbose("  imdb['%s'] = %s" % (key, self.imdbInfo[key]))
        
    ####################################
    #  Extract info from local files
    ####################################
    
    def _getTrailerFile(self):
        """ Return the trailer file in the movie directory. """
        trailerFile = None
        for fileName in os.listdir(self.dirPath):
            fileNameLCase = fileName.lower()
            if (TRAILER_STRING in fileNameLCase):
                trailerFile = fileName
                break
        return trailerFile
        
    ####################################
    #  Required Abstract Functions
    ####################################
    
    def fetchVideoInfo(self, forceUpdate=False, foreign=False):
        """ Populate the *new* variables with information. """
        # Try populating values from the NFO first
        self.nfoInfo = self._getNfoInfo()
        self.imdbUrl = self._getImdbUrlFromNfo()
        if (self.nfoInfo):
            self.title = util.encode(self.nfoInfo.findtext("//movie/title"))
            self.year = self.nfoInfo.findtext("//movie/year")
            self.country = util.encode(self.nfoInfo.findtext("//movie/country"))
            self.aka = util.encode(self.nfoInfo.findtext("//movie/aka"))
            self.imdbUpdate = util.encode(self.nfoInfo.findtext("//movie/imdbupdate"))
            self.trailerUrl = self.nfoInfo.findtext("//movie/trailerurl")
            if (self.year): self.year = int(self.year)
        # If not all required values, get them from IMDB
        if (not self.nfoInfo) or (forceUpdate):
            self.imdbUrl = self.imdbUrl or self._getImdbUrlFromSearch(foreign)
            self.imdbInfo = self._getImdbInfoFromUrl(self.imdbUrl)
            self.imdbUpdate = time.strftime("%Y-%m-%d %H:%M:%S")
            if (self.imdbInfo):
                self._newInfoFound = True
                self.title = self.title or util.encode(self.imdbInfo['title'])
                self.year = self.year or self.imdbInfo['year']
                self.country = self.country or util.encode(self.imdbInfo['country'][0])
                self.aka = self._getAka(self.imdbInfo)
        # Update New DirName and FileNames
        self.updateNewDirName(self.aka if foreign else None)
        self.updateNewFilePrefix(self.aka if foreign else None)
        self.updateNewFileNames()
    
    ####################################
    #  Search and Parse IMDB
    ####################################
        
    def _getImdbUrlFromNfo(self):
        """ Return the IMDB link from the NFO. """
        if (self.curNfoName):
            log.finer("  Searching NFO for IMDB link: %s" % self.curNfoName)
            nfoPath = "%s/%s" % (self.dirPath, self.curNfoName)
            nfoHandle = open(nfoPath, 'r')
            nfoData = nfoHandle.read()
            nfoHandle.close()
            matches = re.findall(IMDB_REGEX, nfoData)
            if (matches):
                return self.getUrl(matches[0])
            log.finer("  IMDB link not found in NFO: %s" % self.curNfoName)
        return None
            
    def _getImdbUrlFromSearch(self, foreign=False):
        """ Search IMDB for the specified title. """
        # Search IMDB for potential matches
        title = self.curTitle
        year = self.curYear or "NA"
        log.info("  Searching IMDB for: '%s' (yr: %s)" % (title, year))
        results = imdbpy.search_movie(title, IMDB_MAX_RESULTS)
        # Check first 5 Results Title and year matches exactly
        selection = None
        for result in results[0:5]:
            if (self._weakMatch(result['title'], title)) and (int(result['year']) == year):
                log.fine("  Result match: %s (%s)" % (result['title'], result['year']))
                selection = result
                break
        # Ask User to Select Correct Result
        if (not selection):
            log.fine("  No exact IMDB match found, prompting user")
            if (not foreign): choiceStr = lambda r: "%s (%s) - %s" % (r['title'], r['year'], self.getUrl(r.movieID))
            else: choiceStr = lambda r: "%s (%s-%s): %s" % (r['title'], self._getCountry(r), r['year'], self._getAka(r))
            selection = util.promptUser(results, choiceStr)
        # If still no selection, return none
        if (not selection):
            log.fine("  IMDB has no entry for: %s (%s)" % (title, year))
            return None
        return self.getUrl(selection.movieID)
            
    def _getImdbInfoFromUrl(self, imdbUrl, logIt=True):
        """ Search IMDB For the movieID's info. """
        try:
            if (not imdbUrl): return None
            if (logIt): log.fine("  Looking up movie: %s" % imdbUrl)
            movieID = re.findall(IMDB_REGEX, imdbUrl)[0]
            return imdbpy.get_movie(movieID)
        except imdb.IMDbDataAccessError:
            log.warn("  IMDB Data Access Error: %s" % imdbUrl)
            return None
        
    def getUrl(self, movieID):
        """ Create an IMDB Url for the specified movieID. """
        return IMDB_REGEX.replace('(\d+?)', movieID)
    
    def _getAka(self, imdbInfo):
        """ Find and return the first English AKA title in the list. """
        imdbpy.update(imdbInfo)
        if (imdbInfo.get('akas')):
            # Check for an English aka
            for akaStr in imdbInfo['akas']:
                if ('::' in akaStr):
                    aka,meta = akaStr.split('::')
                    if ('english' in meta.lower()):
                        return aka
            # English not found; Return the first Entry
            akaStr = imdbInfo['akas'][0]
            if ('::' in akaStr):
                return akaStr.split('::')[0]
            return akaStr
        return None
    
    def _getCountry(self, imdbInfo):
        """ Get the country from imdbInfo. """
        try:
            imdbpy.update(imdbInfo)
            return imdbInfo['country'][0]
        except:
            return None
        
    ####################################
    #  Trailer Searching
    ####################################
    
    def lookupTrailerUrl(self, useAka=False):
        """ Lookup the trailer URL. """
        # No need to search if we already have a trailer
        if (self.trailerUrl):
            log.info("  Trailer URL already exists: %s" % self.trailerUrl)
            return None
        # Search for the Trailer URL
        searchTitle = self.title or self.curTitle
        if (useAka): searchTitle = self.aka or searchTitle
        searchYear = self.year or self.curYear or "NA"
        trailerUrl = self._searchTrailerAddict(searchTitle, searchYear)
        trailerUrl = trailerUrl or self._searchYouTube(searchTitle, searchYear)
        if (not trailerUrl):
            log.fine("  Found no trailer for: '%s' (yr: %s)" % (searchTitle, searchYear))
            return None
        # We found a new Trailer URL! :)
        self._newInfoFound = True
        self.trailerUrl = trailerUrl
        
    def _searchTrailerAddict(self, searchTitle, searchYear):
        """ Search TrailerAddict for a Trailer URL """
        # Search TrailerAddict for the Movie
        log.info("  Searching TrailerAddict for: '%s' (yr: %s)" % (searchTitle, searchYear))
        searchResults = traileraddict.search(searchTitle)
        if (not searchResults):
            log.fine("  TrailerAddict has no search results for: '%s' (yr: %s)" % (searchTitle, searchYear))
            return None
        # Select the correct TrailerAddict Movie
        firstTitle = searchResults[0]['title']
        firstYear = searchResults[0]['year']
        if (firstTitle.lower() == searchTitle.lower()) and (int(firstYear) == searchYear):
            log.fine("  First result is exact match: %s (%s)" % (searchTitle, searchYear))
            searchSelection = searchResults[0]
        else:
            log.fine("  No exact TrailerAddict match found, prompting user")
            choiceStr = lambda r: "%s (%s) - %s" % (r['title'], r['year'], r['url'])
            searchSelection = util.promptUser(searchResults, choiceStr)
        if (not searchSelection):
            log.fine("  TrailerAddict has no entry for: '%s' (yr: %s)" % (searchTitle, searchYear))
            return None
        # Search for the correct Video (Traileraddict has many per movie)
        trailerUrls = traileraddict.getTrailerUrls(searchSelection['url'])
        trailerUrl = traileraddict.getMainTrailer(trailerUrls)
        if (not trailerUrl):
            log.info("  Main trailer not found, prompting user")
            choiceStr = lambda t: t
            trailerUrl = util.promptUser(trailerUrls, choiceStr)
        return trailerUrl
    
    def _searchYouTube(self, searchTitle, searchYear):
        """ Search YouTune for a Trailer URL. """
        log.info("  Searching YouTube for: '%s' (yr: %s)" % (searchTitle, searchYear))
        searchResults = youtube.search(searchTitle)
        # Select the correct YouTube Video (always ask user)
        choiceStr = lambda r: "%s - %s" % (r['title'], r['url'])
        searchSelection = util.promptUser(searchResults, choiceStr)
        if (not searchSelection):
            log.fine("  YouTube has no entry for: '%s' (yr: %s)" % (searchTitle, searchYear))
            return None
        return searchSelection['url']
    
    ####################################
    #  Actions to Perform
    ####################################
    
    def saveNfo(self, foreign=False):
        """ Create the NFO file and store on disk.  Overwrite it if already exists.
            Format: http://xbmc.org/wiki/?title=Import_-_Export_Library#Video_nfo_Files
        """
        # Check we have new Information from the net
        if (self.curNfoName) and (not self._newInfoFound):
            log.fine("  No new info collected, skipping NFO create.")
            return None
        # All Set, Create the NFO!
        nfoPath = "%s/%s.nfo" % (self.dirPath, self.newFilePrefix)
        log.info("  Creating NFO file at: %s" % nfoPath)
        handle = open(nfoPath, 'w')
        handle.write("<xml>\n")
        if (self.imdbUrl): handle.write("  %s\n" % util.escape(self.imdbUrl))
        handle.write("  <movie>\n")
        if (self.title):      handle.write("    <title>%s</title>\n" % util.escape(self.title))
        if (self.year):       handle.write("    <year>%s</year>\n" % util.escape(self.year))
        if (self.country):    handle.write("    <country>%s</country>\n" % util.escape(self.country))
        if (self.aka):        handle.write("    <aka>%s</aka>\n" % util.escape(self.aka))
        if (self.imdbUpdate): handle.write("    <imdbupdate>%s</imdbupdate>\n" % self.imdbUpdate)
        if (self.trailerUrl): handle.write("    <trailerurl>%s</trailerurl>\n" % util.escape(self.trailerUrl))
        handle.write("  </movie>\n")
        handle.write("</xml>\n")
        handle.close()
    
    def downloadTrailer(self):
        """ Download the trailer. """
        # Check we already have a trailer
        if (self.curTrailerName):
            log.info("  Trailer already found: %s/%s" % (self.dirPath, self.curTrailerName))
            return None
        # Check we have a trailerUrl
        if (not self.trailerUrl):
            log.info("  TrailerUrl not found for: %s" % (self.title or self.curTitle))
            return None
        # Make sure the path doesn't already exist
        trailerPath = self.newFileNames[0] or self.curFileNames[0]
        trailerPath = trailerPath.replace('.part1', '')
        trailerPath = "%s/%s-trailer.flv" % (self.dirPath, trailerPath[0:-4])
        if (os.path.exists(trailerPath)):
            log.warn("  Filepath already exists: %s" % trailerPath)
            return None
        # All Set, Download It!
        log.info("  Downloading trailer to: %s" % trailerPath)
        if ('traileraddict.com' in self.trailerUrl):
            traileraddict.downloadTrailer(self.trailerUrl, trailerPath)
        elif ('youtube.com' in self.trailerUrl):
            youtube.downloadTrailer(self.trailerUrl, trailerPath)
            
            