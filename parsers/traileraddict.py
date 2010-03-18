"""
Search and Download Trailers from TrailerAddict
"""
import re
import util
log = util.log

TABASE_URL     = 'http://traileraddict.com{{path}}'
SEARCH_URL     = 'http://www.traileraddict.com/search.php?domains=www.traileraddict.com&sitesearch=www.traileraddict.com&client=pub-8929492375389186&forid=1&channel=4779144239&ie=ISO-8859-1&oe=ISO-8859-1&safe=active&cof=GALT%3A%235A5A5A%3BGL%3A1%3BDIV%3A%23336699%3BVLC%3ACD0A11%3BAH%3Acenter%3BBGC%3AFFFFFF%3BLBGC%3AFFFFFF%3BALC%3ACD0A11%3BLC%3ACD0A11%3BT%3A000000%3BGFNT%3ACD0A11%3BGIMP%3ACD0A11%3BLH%3A50%3BLW%3A227%3BL%3Ahttp%3A%2F%2Fwww.traileraddict.com%2Fimages%2Fgoogle.png%3BS%3Ahttp%3A%2F%2Fwww.traileraddict.com%3BFORID%3A11&hl=en&q={{query}}'
SEARCH_REGEX   = r'<a href="(/tags/.+?)">(.*?)</a>.*?\n.*?(\d{4})</span>'
MOVIE_REGEX    = r'<a href="(/trailer/{{tag}}/.*?)">.*?</a>'
VIDEONUM_REGEX = r'<param name="movie" value="http://www.traileraddict.com/emb/(\d+)">'
FLASH_URL      = r'http://www.traileraddict.com/fvar.php?tid={{videonum}}'
FLASH_REGEX    = r'fileurl=(.+?.flv)&'


def search(title):
    """ Search for the specified movie.
        @param title: Title of the movie to search for
    """
    # Fetch the HTML for the search page
    query = title.replace(" ", "+")
    searchUrl = SEARCH_URL.replace('{{query}}', query)
    searchHtml = util.getHtml(searchUrl)
    results = re.findall(SEARCH_REGEX, searchHtml)
    # Parse and return the search results
    searchResults = []
    for result in results:
        searchResult = {}
        searchResult['url'] = TABASE_URL.replace('{{path}}', result[0])
        searchResult['title'] = result[1]
        searchResult['year'] = result[2]
        searchResults.append(searchResult)
    return searchResults


def getTrailerUrls(movieUrl):
    """ Return the trailers on the specified link.
        @param movieUrl: URL to movie info on TrailerAddict
    """
    tag = movieUrl.split('/')[-1]
    movieHtml = util.getHtml(movieUrl)   
    movieRegex = MOVIE_REGEX.replace('{{tag}}', tag)
    results = re.findall(movieRegex, movieHtml)
    trailerUrls = map(lambda r: TABASE_URL.replace('{{path}}', r), results)
    return list(set(trailerUrls))  # Remove Duplicates

    
def getMainTrailer(trailerResults):
    """ Return the main trailer if it exists. """
    for trailerLink in trailerResults:
        if (trailerLink.endswith('/trailer')):
            return trailerLink
    return None


def downloadTrailer(trailerUrl, filePath):
    """ Download the specified trailer.
        @param trailerUrl: Trailer URL (ex: /trailer/the-terminal/trailer)
        @param filePath: Path to save trailer
    """
    trailerHtml = util.getHtml(trailerUrl)
    videoNumbers = re.findall(VIDEONUM_REGEX, trailerHtml)
    flashUrl = FLASH_URL.replace('{{videonum}}', videoNumbers[0])
    flashResponse = util.getHtml(flashUrl)
    fileUrl = re.findall(FLASH_REGEX, flashResponse)[0]
    util.downloadFile(fileUrl, filePath)
