# coding=UTF-8
"""
Video Group object, main object behind each Video (Movie or TV series).
NFO Reference: http://xbmc.org/wiki/?title=Nfo
"""
import os
import re
import util
from util import log
from elementtree import ElementTree

VIDEO_TAGS        = ['xvid', 'divx', 'bdrip', 'hdrip', 'dvdrip', 'dvdscr', 'dvd', 'r5', 'scr', 'repack', 'ac3']
REPLACE_CHARS     = {'&':'and', "'":'', '?':'', ':':' -', ',':'', '!':''}
VIDEO_EXTENSIONS  = ['avi', 'iso', 'mkv', 'mp4', 'mpg']   # Valid video extensions
SUBTITLE_DIRS     = ['', 'subs', 'subtitles']             # Sub directories that subs may exists
STOP_WORDS        = ['the', 'a']                          # Bad words for beginning of titles
INVALID_CHARS     = '/<>,:"\'\\|{}@#$%^&*+=~`()'          # Invalid File and Dir name chartacters
SAMPLE_STRING     = 'samp'                                # String to catch samples
MEGABYTE          = 1048576                               # 1 megabyte in bytes
MIN_VIDEO_MB      = 100 * MEGABYTE                        # Min size of valid videos (bytes)


class Video:
    """ Represents a video or TV series on Disk. """
    
    def __init__(self, dirPath):
        log.title("Processing Directory: %s" % dirPath)
        # Local files and directories
        self.dirPath        = dirPath                    # Directory containing Videos
        self.curDirName     = os.path.basename(dirPath)  # Current DirName (video title)
        self.curFileNames   = self._getVideoFiles()      # Current AVI FileNames
        self.curNfoName     = self._getNfoFile()         # Current NFO FileName
        # Info from File or DirNames (not from NFO)
        self.subsFound      = False                      # True if any subtitle files found
        self.curTitle       = self._getCurrentTitle()    # Video title pulled from dirName
        self.curYear        = self._getCurrentYear()     # Video year pulled from dirName
        self.extention      = self._getExtention()       # File extention (.avi, .mkv, .iso, etc)
        self.videoTags      = self._getVideoTags()       # Bits of info like xvid, r5, etc
        self.subtitles      = self._getSubtitles()       # Subtitle files for video
        # New info after parsing NFO or Web
        self.nfoInfo        = None                       # ElementTree built from curNfoName
        self.title          = None                       # New Title for the video
        self.year           = None                       # New Year for the video
        self.country        = None                       # New Country for the video
        self.aka            = None                       # New AKA Title for the video
        # New DirName and FileNames
        self.newDirName     = None                       # New DirName to place video files
        self.newFilePrefix  = None                       # New FileName prefix for videos, nfo, etc
        self.newFileNames   = []                         # New FileNames for video files
        
    def __str__(self):
        """ String representation of this object. """
        return "<Video: %s (%s)>" % (self.curTitle, self.curYear)
        
    ####################################
    #  Required abstract functions
    ####################################
    
    def _updateVideoInfo(self):
        """ Populate the *new* variables with information. """
        raise Exception("Error: _updateVideoInfo() not implemented in child class.")
        
    ####################################
    #  Extract info from local files
    ####################################
    
    def _getVideoFiles(self):
        """ Return the AVI files that make up this video. """
        videoFiles = []
        for fileName in os.listdir(self.dirPath):
            filePath = "%s/%s" % (self.dirPath, fileName)
            test1 = SAMPLE_STRING not in fileName.lower()
            test2 = os.path.getsize(filePath) >= MIN_VIDEO_MB
            for ext in VIDEO_EXTENSIONS:
                test3 = fileName.lower().endswith(ext)
                if (test1 and test2 and test3):
                    videoFiles.append(fileName)
        if (not videoFiles):
            log.warn("  No video files found for: %s" % self.dirPath)
        return sorted(videoFiles)
        
    def _getSubtitles(self):
        """ Return subtitle files for this video. """
        subtitles = []
        for path in SUBTITLE_DIRS:
            dirPath = "%s/%s" % (self.dirPath, path)
            if (os.path.exists(dirPath)):
                for fileName in os.listdir(dirPath):
                    if (fileName.endswith('.srt')):
                        self.subsFound = True
                        subtitles.append("%s/%s" % (path, fileName))
                    elif (fileName.endswith('.idx')):
                        self.subsFound = True
                        if (self._idxSubtitlesOK(dirPath, fileName)):
                            subtitles.append("%s/%s" % (path, fileName))
                    elif (fileName.endswith('.sub')):
                        self.subsFound = True
        # Check we have same number of subtitles as video files
        if (subtitles) and (len(subtitles) != len(self.curFileNames)):
            log.warn("  Mismatch between len(videos) and len(subtitles): %s" % self.dirPath)
            return None
        return sorted(subtitles)
        
    def _idxSubtitlesOK(self, dirPath, fileName):
        """ Return subtitles if the idx, sub names match up, otherwise []. """
        subPath = "%s/%s.sub" % (dirPath, fileName[0:-4])
        idxPath = "%s/%s.idx" % (dirPath, fileName[0:-4])
        if (not os.path.exists(subPath) or not os.path.exists(idxPath)):
            log.warn("  Subtitle Error: %s/%s" % (dirPath, fileName))
            return False
        return True
        
    def _getNfoFile(self):
        """ Return the first NFO file in the video directory. """
        for fileName in os.listdir(self.dirPath):
            fileNameLCase = fileName.lower()
            if (fileNameLCase.endswith('.nfo')):
                return fileName
        return None
    
    def _getCurrentTitle(self):
        """ Return the title for this video pulled from the dirname. """
        square = self.curDirName.find('[')
        paren = self.curDirName.find('(')
        choices = filter(lambda n: n>0, [square, paren])
        if (choices):
            end = min(choices)
            return self.curDirName[0:end].strip()
        return self.curDirName
        
    def _getCurrentYear(self):
        """ Return the year of this video pulled from the dirname or filenames. """
        regex = r'[\[\(\-\.\s\_]([1|2]\d\d\d)'
        for name in [self.curDirName] + self.curFileNames:
            matches = re.findall(regex, name)
            if (matches): return int(matches[0])
        return None
    
    def _getExtention(self):
        """ Reutrn the video extention. """
        extention = None
        if (self.curFileNames):
            extention = self.curFileNames[0].split('.')[-1]
        return extention
    
    def _getVideoTags(self):
        """ Return the rip information. """
        videoTags = set()
        for fileName in self.curFileNames:
            fileName = fileName.lower()
            for infoStr in VIDEO_TAGS:
                if (infoStr in fileName):
                    videoTags.add(infoStr)
                    fileName = fileName.replace(infoStr, '')
        return list(videoTags)
    
    def _getNfoInfo(self):
        """ Return ElementTree object if NFO file exists. """
        if (self.curNfoName):
            try:
                nfoPath = "%s/%s" % (self.dirPath, self.curNfoName)
                return ElementTree.parse(nfoPath)
            except Exception, e:
                log.warn("  Invalid NFO file: %s; %s" % (nfoPath, e))
        return None
    
    def _weakMatch(self, title1, title2):
        """ Return TRUE if the two titles match after some string manipulation. """
        # Manipulate Title 1
        title1 = title1.lower()
        title1 = util.replaceChars(title1, REPLACE_CHARS)
        title1 = util.removePrefixWords(title1, STOP_WORDS)
        if (title1.endswith('the')): title1 = title1[0:-3]
        title1 = title1.strip()
        # Manipulate Title 2
        title2 = title2.lower()
        title2 = util.replaceChars(title2, REPLACE_CHARS)
        title2 = util.removePrefixWords(title2, STOP_WORDS)
        if (title2.endswith('the')): title2 = title2[0:-3]
        title2 = title2.strip()
        # Return the Comparison
        #log.info("Checking match '%s' and '%s'" % (title1, title2))
        return title1 == title2
    
    ####################################
    #  List Functions
    ####################################
    
    def getNoVideoList(self):
        """ Return list entry if this directory is missing video files. """
        if (not self.curFileNames):
            return [self.dirPath]
        return []
    
    def getBadNfoList(self):
        """ Return list entries for any invalid nfos in video dir. """
        nfolist = []
        for fileName in os.listdir(self.dirPath):
            fileNameLCase = fileName.lower()
            if (fileNameLCase.endswith('.nfo')):
                nfoPath = "%s/%s" % (self.dirPath, fileName)
                try:
                    info = ElementTree.parse(nfoPath)
                    #assert info.findtext("//movie/title") != "None"
                except Exception, e:
                    nfolist.append(nfoPath)
        return nfolist
                    
    def getMissingNfoList(self):
        """ Return list entry if this movie is missing an nfo. """
        if (not self.curNfoName):
            return [self.dirPath]
        return []
    
    def getHasSubtitleList(self):
        """ Return list entry for each video with valid subtitles. """
        if (self.subtitles):
            return [self.dirPath]
        return []
        
    def getNoSubtitleList(self):
        """ Return list entry for each video with no subtitles. """
        if (not self.subsFound):
            return [self.dirPath]
        return []
        
    def getSubtitleErrorList(self):
        """ Return list entry for each video with Subtitle Errors. A Subtitle
            Error is anything that this program cannot understand.
        """
        if (not self.subtitles and self.subsFound):
            return [self.dirPath]
        return []
    
    ####################################
    #  Update New Dir & FileName
    ####################################
    
    def updateNewDirName(self, aka=None):
        """ Update the new DirName to place video files.
            Format: http://forum.boxee.tv/showthread.php?t=5214
            @param aka: Optional alternative title (useful for foreign videos)
        """
        year = self.year or self.curYear
        self.newDirName = aka or self.title or self.curTitle
        self.newDirName = util.replaceChars(self.newDirName, REPLACE_CHARS)
        self.newDirName = util.removeChars(self.newDirName, INVALID_CHARS)
        self.newDirName = util.removePrefixWords(self.newDirName, STOP_WORDS)
        self.newDirName = util.removeExtraChars(self.newDirName, '.')
        if (aka) and (year): self.newDirName = "%s (%s-%s)" % (self.newDirName, self.country, year)
        elif (aka): self.newDirName = "%s (%s)" % (self.newDirName, self.country)
        elif (year): self.newDirName = "%s (%s)" % (self.newDirName, year)
    
    def updateNewFilePrefix(self, aka=None):
        """ Update the new FileName prefix for videos, nfo, etc
            Format: http://forum.boxee.tv/showthread.php?t=5214
            @param aka: Optional alternative title (useful for foreign videos)
        """
        year = self.year or self.curYear
        self.newFilePrefix = aka or self.title or self.curTitle
        self.newFilePrefix = util.replaceChars(self.newFilePrefix, REPLACE_CHARS)
        self.newFilePrefix = util.removeChars(self.newFilePrefix, INVALID_CHARS)
        self.newFilePrefix = self.newFilePrefix.replace(' ', '.')
        self.newFilePrefix = util.removeExtraChars(self.newFilePrefix, '.')
        self.newFilePrefix = self.newFilePrefix.lower()
        if (year): self.newFilePrefix = "%s.(%s)" % (self.newFilePrefix, year)
        
    def updateNewFileNames(self):
        """ Update the new FileNames for videos.
            See: updateNewFilePrefix() documentation for more details.
        """
        includeCount = len(self.curFileNames) >= 2
        self.newFileNames = []
        count = 0
        for fileName in sorted(self.curFileNames):
            extension = fileName.split('.')[-1].lower()
            newFileName = self.newFilePrefix
            if (includeCount): newFileName += ".part%s" % str(count+1)
            if (self.videoTags): newFileName += "-%s" % '.'.join(self.videoTags)
            newFileName += ".%s" % extension
            self.newFileNames.append(newFileName)
            count += 1
            
    ####################################
    #  Actions to Perform
    ####################################
    
    def renameFiles(self, skipImdb=False):
        """ Rename the Video files. """
        # Make sure we have new FileNames
        if (not self.newFileNames) or (skipImdb):
            log.info("  IMDB Information not available: Skipping renameFiles.")
            return None
        # Rename the Video Files
        for i in range(len(self.newFileNames)):
            curFilePath = "%s/%s" % (self.dirPath, self.curFileNames[i])
            newFilePath = "%s/%s" % (self.dirPath, self.newFileNames[i])
            self._rename(curFilePath, newFilePath)
        # Other files need the same filenames
        self._renameNfo()
        self._renameSubtitles()
        
    def _renameNfo(self):
        """ Rename the NFO to files. """
        if (self.curNfoName):
            curNfoPath = "%s/%s" % (self.dirPath, self.curNfoName)
            newNfoPath = "%s/%s.nfo" % (self.dirPath, self.newFilePrefix)
            self._rename(curNfoPath, newNfoPath)
    
    def _renameSubtitles(self):
        """ Rename the Subtitle files. """
        includeCount = len(self.curFileNames) >= 2
        if (self.subtitles):
            for i in range(len(self.subtitles)):
                subPath = self.subtitles[i]
                newFilePrefix = self.newFileNames[i][0:-4]
                # Make sure the subtitle directory exists
                newSubDirPath = "%s/subtitles" % (self.dirPath)
                if (not os.path.exists(newSubDirPath)):
                    log.info("  >> Creating Dir: %s" % newSubDirPath)
                    os.mkdir(newSubDirPath, 0755)
                # Rename SRT Files
                if (subPath.lower().endswith('.srt')):
                    curSrtPath = "%s/%s" % (self.dirPath, subPath)
                    newSrtPath = "%s/%s.srt" % (newSubDirPath, newFilePrefix)
                    self._rename(curSrtPath, newSrtPath)
                # Rename IDX, SUB Files
                elif (subPath.lower().endswith('.idx')):
                    curIdxPath = "%s/%s" % (self.dirPath, subPath)
                    curSubPath = "%s.sub" % (curIdxPath[0:-4])
                    newIdxPath = "%s/%s.idx" % (newSubDirPath, newFilePrefix)
                    newSubPath = "%s/%s.sub" % (newSubDirPath, newFilePrefix)
                    self._rename(curIdxPath, newIdxPath)
                    self._rename(curSubPath, newSubPath)
                    
    def renameDirectory(self):
        if (self.newDirName):
            curDirPath = self.dirPath
            newDirPath = "%s/%s" % (curDirPath[0:curDirPath.rfind('/')], self.newDirName)
            self._rename(curDirPath, newDirPath)
            
    def _rename(self, src, dst):
        """ Rename the specified file. """
        if (src != dst):
            if (os.path.exists(dst)):
                log.warn("  Path already exists: %s" % dst)
                return None
            log.info("  >> Renaming: %s" % src)
            log.info("           to: %s" % dst)
            os.rename(src, dst)
            