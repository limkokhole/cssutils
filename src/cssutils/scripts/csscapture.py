#!/usr/bin/env python
"""Retrieve all CSS stylesheets including embedded for a given URL.
Retrieve as StyleSheetList or save to disk - raw, parsed or minified version.

TODO:
- maybe use DOM 3 load/save?
- logger class which handles all cases when no log is given...
- saveto: why does urllib2 hang?
"""
__all__ = ['CSSCapture']
__docformat__ = 'restructuredtext'
__version__ = '$Id$'

import codecs
import errno
import HTMLParser
import logging
import os
import sys
import urllib2
import urlparse

import cssutils
try:
    import cssutils.encutils as encutils
except ImportError:
    try:
        import encutils
    except ImportError:
        sys.exit("You need encutils from http://cthedot.de/encutils/")

# types of sheets in HTML
LINK = 0 # <link rel="stylesheet" type="text/css" href="..." [@title="..." @media="..."]/>
STYLE = 1 # <style type="text/css" [@title="..."]>...</style>

class CSSCaptureHTMLParser(HTMLParser.HTMLParser):
    """ parses given data for link and style elements """
    curtag = u''
    sheets = [] # (type, [atts, cssText])

    def _loweratts(self, atts):
        return dict([(a.lower(), v.lower()) for a, v in atts])

    def handle_starttag(self, tag, atts):
        if tag == u'link':
            atts = self._loweratts(atts)
            if u'text/css' == atts.get(u'type', u''):
                self.sheets.append((LINK, atts))
        elif tag == u'style':
            # also get content of style
            atts = self._loweratts(atts)
            if u'text/css' == atts.get(u'type', u''):
                self.sheets.append((STYLE, [atts, u'']))
                self.curtag = tag
        else:
            # close as only intersting <style> cannot contain any elements
            self.curtag = u''

    def handle_data(self, data):
        if self.curtag == u'style':
            self.sheets[-1][1][1] = data # replace cssText

    def handle_comment(self, data):
        # style might have comment content, treat same as data
        self.handle_data(data)

    def handle_endtag(self, tag):
        # close as style cannot contain any elements
        self.curtag = u''


class CSSCapture(object):
    """
    Retrieve all CSS stylesheets including embedded for a given URL.
    Optional setting of User-Agent used for retrieval possible
    to handle browser sniffing servers.

    raises urllib2.HTTPError
    """
    def __init__(self, ua=None, log=None, defaultloglevel=logging.INFO):
        """
        initialize a new Capture object

        ua
            init User-Agent to use for requests
        log
            supply a log object which is used instead of the default
            log which writes to sys.stderr
        defaultloglevel
            constant of logging package which defines the level of the
            default log if no explicit log given
        """
        self._ua = ua

        if log:
            self._log = log
        else:
            self._log = logging.getLogger('CSSCapture')
            hdlr = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter('%(message)s')
            hdlr.setFormatter(formatter)
            self._log.addHandler(hdlr)
            self._log.setLevel(defaultloglevel)
            self._log.debug(u'Using default log')

        self._htmlparser = CSSCaptureHTMLParser()
        self._cssparser = cssutils.CSSParser(log = self._log)

    def _doRequest(self, url):
        """Do an HTTP request

        Return (url, rawcontent)
            url might have been changed by server due to redirects etc
        """
        self._log.debug(u'    CSSCapture._doRequest\n        * URL: %s' % url)

        req = urllib2.Request(url)
        if self._ua:
            req.add_header('User-agent', self._ua)
            self._log.info('        * Using User-Agent: %s', self._ua)
            
        try:
            res = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            self._log.critical('    %s\n%s %s\n%s' % (
                e.geturl(), e.code, e.msg, e.headers))
            return None, None

        # get real url
        if url != res.geturl():
            url = res.geturl()
            self._log.info('        URL retrieved: %s', url)

        return url, res

    def _createStyleSheet(self, href=None, 
                          media=None, 
                          parentStyleSheet=None, 
                          title=u'',
                          cssText=None,
                          encoding=None):
        """
        Return CSSStyleSheet read from href or if cssText is given use that.
        
        encoding
            used if inline style found, same as self.docencoding
        """
        if cssText is None:
            encoding, cssText = cssutils.util._readUrl(href, parentEncoding=self.docencoding)
            encoding = None # already decoded???

        sheet = self._cssparser.parseString(cssText, href=href, media=media, title=title,
                                            encoding=encoding)
        
        if not sheet:
            return None

        else:
            self._log.info(u'    %s\n' % sheet)
            self._nonparsed[sheet] = cssText
            return sheet

    def _findStyleSheets(self, docurl, doctext):
        """
        parse text for stylesheets
        fills stylesheetlist with all found StyleSheets

        docurl
            to build a full url of found StyleSheets @href
        doctext
            to parse
        """
        # TODO: ownerNode should be set to the <link> node
        self._htmlparser.feed(doctext)
        
        for typ, data in self._htmlparser.sheets:
            sheet = None
            
            if LINK == typ:
                self._log.info(u'+ PROCESSING <link> %r' % data)

                atts = data
                href = urlparse.urljoin(docurl, atts.get(u'href', None))
                sheet = self._createStyleSheet(href=href,
                                               media=atts.get(u'media', None),
                                               title=atts.get(u'title', None))
            elif STYLE == typ:
                self._log.info(u'+ PROCESSING <style> %r' % data)

                atts, cssText = data
                sheet = self._createStyleSheet(cssText=cssText,
                                               href = docurl,
                                               media=atts.get(u'media', None),
                                               title=atts.get(u'title', None),
                                               encoding=self.docencoding)
                if sheet:
                    sheet._href = None # inline have no href!
                print sheet.cssText 
                                               
            if sheet:
                self.stylesheetlist.append(sheet)
                self._doImports(sheet, base=docurl)


    def _doImports(self, parentStyleSheet, base=None):
        """
        handle all @import CSS stylesheet recursively
        found CSS stylesheets are appended to stylesheetlist
        """
        # TODO: only if not parsed these have to be read extra!
        
        for rule in parentStyleSheet.cssRules:
            if rule.type == rule.IMPORT_RULE:
                self._log.info(u'+ PROCESSING @import:')
                self._log.debug(u'    IN: %s\n' % parentStyleSheet.href)
                sheet = rule.styleSheet                
                href = urlparse.urljoin(base, rule.href)
                if sheet:
                    self._log.info(u'    %s\n' % sheet)
                    self.stylesheetlist.append(sheet)
                    self._doImports(sheet, base=href)

    def capture(self, url):
        """
        Capture all stylesheets at given urls HTML document. 
        Any HTTPError is raised to caller.

        url
            to capture CSS from

        Returns ``cssutils.stylesheets.StyleSheetList``.
        """
        self._log.info(u'\nCapturing CSS from URL:\n    %s\n', url)
        self._nonparsed = {}
        self.stylesheetlist = cssutils.stylesheets.StyleSheetList()
            
        # used to save inline styles
        scheme, loc, path, query, fragment = urlparse.urlsplit(url)
        self._filename = os.path.basename(path)

        # get url content
        url, res = self._doRequest(url)
        if not res:
            sys.exit(1)
            
        rawdoc = res.read()
            
        self.docencoding = encutils.getEncodingInfo(
            res, rawdoc, log=self._log).encoding
        self._log.info(u'\nUsing Encoding: %s\n', self.docencoding)

        doctext = rawdoc.decode(self.docencoding)

        # fill list of stylesheets and list of raw css
        self._findStyleSheets(url, doctext)

        return self.stylesheetlist

    def saveto(self, dir, saveraw=False, minified=False):
        """
        saves css in "dir" in the same layout as on the server
        internal stylesheets are saved as "dir/__INLINE_STYLE__.html.css"

        dir
            directory to save files to
        saveparsed
            save literal CSS from server or save the parsed CSS
        minified
            save minified CSS
            
        Both parsed and minified (which is also parsed of course) will
        loose information which cssutils is unable to understand or where
        it is simple buggy. You might to first save the raw version before
        parsing of even minifying it.
        """
        msg = 'parsed'
        if saveraw:
            msg = 'raw'
        if minified:
            cssutils.ser.prefs.useMinified()
            msg = 'minified'
        
        inlines = 0
        for i, sheet in enumerate(self.stylesheetlist):
            url = sheet.href
            if not url:
                inlines += 1
                url = u'%s_INLINE_%s.css' % (self._filename, inlines)
                
            # build savepath
            scheme, loc, path, query, fragment = urlparse.urlsplit(url)
            # no absolute path
            if path and path.startswith('/'):
                path = path[1:]
            path = os.path.normpath(path)
            path, fn = os.path.split(path)
            savepath = os.path.join(dir, path)
            savefn = os.path.join(savepath, fn)
            try:
                os.makedirs(savepath)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise e
                self._log.debug(u'Path "%s" already exists.', savepath)

            self._log.info(u'SAVING %s, %s %r' % (i+1, msg, savefn))
            
            sf = open(savefn, 'wb')
            if saveraw:
                cssText = self._nonparsed[sheet]
                uf = codecs.getwriter('css')(sf)
                uf.write(cssText)
            else:
                sf.write(sheet.cssText)
            sf.close()

def main(args=None):
    import optparse

    usage = "usage: %prog [options] URL"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-d', '--debug', action='store_true', dest='debug',
        help='show debug messages during capturing')
    parser.add_option('-m', '--minified', action='store_true', dest='minified',
        help='saves minified version of captured files')
    parser.add_option('-n', '--notsave', action='store_true', dest='notsave',
        help='if given files are NOT saved, only log is written')
#    parser.add_option('-r', '--saveraw', action='store_true', dest='saveraw',
#        help='if given saves raw css otherwise cssutils\' parsed files')
    parser.add_option('-s', '--saveto', action='store', dest='saveto',
        help='saving retrieved files to "saveto", defaults to "_CSSCapture_SAVED"')
    parser.add_option('-u', '--useragent', action='store', dest='ua',
        help='useragent to use for request of URL, default is urllib2s default')
    options, url = parser.parse_args()
    
    options.saveraw = False # TODO

    if not url:
        parser.error('no URL given')
    else:
        url = url[0]

    if options.debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    # START
    c = CSSCapture(ua=options.ua, defaultloglevel=level)

    stylesheetlist = c.capture(url)

    if options.notsave is None or not options.notsave:
        if options.saveto:
            saveto = options.saveto
        else:
            saveto = u'_CSSCapture_SAVED'
        c.saveto(saveto, saveraw=options.saveraw, minified=options.minified)
    else:
        for i, s in enumerate(stylesheetlist):
            print u'''%s.
    encoding: %r
    title: %r
    href: %r''' % (i + 1, s.encoding, s.title, s.href)


if __name__ == "__main__":
    sys.exit(main())
