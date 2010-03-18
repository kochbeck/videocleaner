"""
Search and Download Trailers from YouTube
"""
import re
import util
log = util.log

SEARCH_URL     = "http://video.google.com/videosearch?q=site%3Ayoutube.com+{{query}}+trailer&emb=0&aq=f"
SEARCH_REGEX   = r'<div class=rl-title>.*?<a href=(.+?)\s.*?>(.+?)</a>.*?<div class=rl-details><span>(.+?)\s-</span>'
ID_REGEX       = r'\?.*?v=(.+?)(&.*?)*$'
T_PARAM_REGEX  = r', "t": "([^"]+)"'
VIDEO_URL      = "http://www.youtube.com/get_video?video_id=%s&t=%s"


def search(title):
    """ Search for the specified movie.
        @param title: Title of the movie to search for
    """
    # Fetch the HTML for the search page
    query = title.replace(" ", "+")
    searchUrl = SEARCH_URL.replace('{{query}}', query)
    searchHtml = util.getHtml(searchUrl)
    searchHtml = searchHtml.replace("\n", "")
    results = re.findall(SEARCH_REGEX, searchHtml)
    # Parse and return the search results
    searchResults = []
    for result in results:
        searchResult = {}
        searchResult['url'] = result[0]
        searchResult['title'] = result[1].replace("<em>", "").replace("</em>", "")
        searchResult['length'] = result[2]
        searchResults.append(searchResult)
    return searchResults


def downloadTrailer(trailerUrl, filePath):
    """ Download the specified trailer.
        @param trailerUrl: Trailer URL (ex: /trailer/the-terminal/trailer)
        @param filePath: Path to save trailer
    """
    videoHtml = util.getHtml(trailerUrl)
    videoId = re.findall(ID_REGEX, trailerUrl)[0][0]
    tParam = re.findall(T_PARAM_REGEX, videoHtml)[0]
    fileUrl = VIDEO_URL % (videoId, tParam)
    util.downloadFile(fileUrl, filePath)
