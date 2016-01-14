#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Recursively walk over the pages of a web site and display the links to
other pages as defined by href and src attributes. It is useful for
understanding how a web site is layed out.

It reports the full path to each page as it encounters it. If the page
does not exist a warning is generated so this tool can be used to find
bad links.

There are options to filter the output so that you restrict what is
reported to interesting files like this with '.css' or '.txt'
extensions.

It can also print a more hierarchical view using indentation and
relative paths.

In addition to just analyzing a site, it can also create a full or
partial mirror based on the filtering.

It is useful for understanding how a web site is layed out or for
finding data files to download.
'''
# License: Open Source MIT
# Copyright (c) Joe Linoff
import argparse
import getpass
import os
import re
import socket
import ssl
import string
import sys

try:
    from html.parser import HTMLParser
    import urllib.request as UrlRequest  # UrlRequest.urlopen()
    import urllib.error as UrlError
except ImportError:
    from HTMLParser import HTMLParser
    import urllib2 as UrlRequest  # UrlRequest.urlopen()
    import urllib2 as UrlError
    ConnectionError = OSError  # only in python3


VERSION = '0.1.0'  # Initial release.


class MyHtmlParser(HTMLParser):
    '''
    Grab all of the file references from a page.

    The user must call analyze() to parse the html data instead of feed().
    '''
    def analyze(self, url, html):
        '''
        Analyze the HTML.
        '''
        self.__setup(url)
        self.feed(html)

    def __setup(self, url):
        setattr(self, 'm_list', [])
        setattr(self, 'm_url', self.__clean_url(url))
        setattr(self, 'm_base', None)

    @staticmethod
    def __clean_url(url):
        clean = url.replace('://', '@@@').replace('//', '/').replace('@@@', '://')
        return clean

    @staticmethod
    def __get_attr(attrs, key):
        for apair in attrs:
            if apair[0].lower() == key:
                return apair[1]
        return None

    @staticmethod
    def __path_join(parta, partb):
        if parta.endswith('/'):
            if partb.startswith('/'):
                return parta + partb[1:]
            else:
                return parta + partb
        elif partb.startswith('/'):
            return parta + partb
        return parta + '/' + partb

    def __create_url(self, in_path):
        path = self.__clean_url(in_path.split('?', 1)[0])
        if path == '/':
            return None  # skip this URL

        if path.startswith('/'):
            # Handle the special case of a BASE reference:
            #  href="/foo"
            if self.m_base is not None:
                path = self.__path_join(self.m_base, path)
            else:
                pos = self.m_url.find('://')
                if pos >= 0:
                    pos = self.m_url.find('/', pos+3)
                else:
                    pos = self.m_url.find('/')
                if pos < 0:
                    return None
                base = self.m_url[:pos]
                path = self.__path_join(base, path)
        elif path.find('://') < 0:
            path = self.__path_join(self.m_url, path)  # prepend the URL

        return path

    def handle_starttag(self, tag, attrs):
        assert getattr(self, 'm_list', None) is not None
        tag = tag.lower()
        if tag == 'base':
            href = self.__get_attr(attrs, 'href')
            if href is not None:
                setattr(self, 'm_base', self.__clean_url(href))
        elif tag in ['a', 'link']:
            href = self.__get_attr(attrs, 'href')
            if href is not None:
                if href.startswith('#') or href.startswith('?'):
                    return  # skip tags
                path = self.__create_url(href)
                if path is not None and path != self.m_url and path not in self.m_list:
                    self.m_list.append(path)  # add the path if it is unique.

        elif tag == 'script':
            src = self.__get_attr(attrs, 'src')
            if src is not None:
                path = self.__create_url(src)
                if path is not None and path != self.m_url and path not in self.m_list:
                    self.m_list.append(path)  # add the path if it is unique.

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        pass


def clean_url(url):
    '''
    Clean a URL to remove extraneous slashes.
    '''
    clean = url.replace('://', '@@@').replace('//', '/').replace('@@@', '://')
    return clean


def proceed(url, opts, dups, depth):
    '''
    Proceed?
    '''
    # honor the depth request
    if opts.depth > 0 and depth > opts.depth:
        return False

    # skip duplicates
    if url in dups:
        return False

    # excludes
    if opts.exclude is not None:
        for pattern in opts.exclude_compiled:
            match = pattern.search(url)
            if match:
                return False

    # includes
    if opts.include is not None:
        for pattern in opts.include_compiled:
            match = pattern.search(url)
            if match is None:
                return False

    return True  # proceed


def openurl(url, opts):
    '''
    Open the current URL.

    Handle authentication, capture exceptions.
    '''
    try:
        if opts.authenticate:
            username = opts.authenticate[0]
            password = opts.authenticate[1]
            pman = UrlRequest.HTTPPasswordMgrWithDefaultRealm()
            pman.add_password(None, url, username, password)

            auth = UrlRequest.HTTPBasicAuthHandler(pman)
            opener = UrlRequest.build_opener(auth)
            UrlRequest.install_opener(opener)

            # CITATION: http://stackoverflow.com/questions/19268548/python-ignore-certicate-validation-urllib2
            # Disable verification - to workaround invalid internal certificates.
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            response = UrlRequest.urlopen(url, context=context)
        else:
            response = UrlRequest.urlopen(url)
        return response

    except UrlError.HTTPError as exc:
        if opts.no_warnings is False:
            sys.stderr.write('WARNING: {}: {}\n'.format(str(exc), url))

    except UrlError.URLError as exc:
        if opts.no_warnings is False:
            sys.stderr.write('WARNING: {}: {}\n'.format(str(exc), url))

    except ConnectionError as exc:
        if opts.no_warnings is False:
            sys.stderr.write('WARNING: {}: {}\n'.format(str(exc), url))

    except socket.timeout as exc:
        if opts.no_warnings is False:
            sys.stderr.write('WARNING: {}: {}\n'.format(str(exc), url))

    return None


def read_url_data(response):
    '''
    Read the URL data.
    '''
    try:
        charset = response.headers.get_content_charset()
    except AttributeError:
        charset = response.headers.getparam('charset')
    if charset is not None:
        data = response.read().decode(charset)  # use the charset to decode
    else:
        data = response.read()  # just read the raw bytes
    return data


def display(url, opts):
    '''
    Should this URL be displayed?

    Return True if it should be displayed or False otherwise.
    '''
    if opts.filter:
        # Handle the special case of index.html.
        urlx = url
        if url.endswith('/'):
            urlx += 'index.html'
        for pattern in opts.filter_compiled:
            if pattern.search(urlx):
                return True  # display - it matches
        return False  # doesn't match - don't display it
    return True  # display it


def report(url, opts, response, info, outpath, depth, parent):
    '''
    Report the URL.

    The data is returned because we might have to read the response
    and we don't want to duplicate that.
    '''
    write = sys.stdout.write
    data = None
    if opts.verbose > 0:  # size
        clen = -1
        key = 'Content-Length'
        if key in info:
            clen = info[key]
        else:
            data = read_url_data(response)
            clen = len(data)
        write('{:>10}  '.format(clen))

    if opts.verbose > 1:  # type
        ctype = 'Unknown'
        key = 'Content-Type'
        if key in info:
            ctype = info[key]
        write('{:<32}  '.format(ctype[:32]))

    # Write out the URL.
    # Handle the indentation.
    if opts.indent:
        if depth:
            indent = depth * opts.spaces_per_indent
            indent_str = indent*' '
            write(indent_str)

    # Write out the URL.
    if opts.relurl:
        if url.startswith(str(parent)):
            relurl = url[len(parent):]
        elif str(parent).startswith(str(url)):
            # Look for backward references.
            tmp = parent[len(url):]
            relurl = ''.join(['../' for _ in range(string.count(tmp, '/'))])
        else:
            relurl = url
        write('{}'.format(relurl))
    else:
        write('{}'.format(url))

    if opts.replicate:
        write(' --> {}'.format(outpath))
    write('\n')

    if opts.verbose >= 3:  # header
        print('    ' + '\n    '.join(str(info).split('\n')))
        data = response.read().decode('utf-8', errors='ignore')

    return data


def replicate_outpath(url, opts):
    '''
    Get the output file name.
    '''
    if opts.replicate:
        pos = len(opts.URL)
        if url.endswith('/'):
            url += 'index.html'
        outpath = url[pos:]
        if outpath.startswith('/') is False:
            outpath = '/' + outpath
        outpath = clean_url(opts.replicate + outpath)
        return outpath
    return None


def replicate(url, opts, response, data, outpath):
    '''
    Replicate the file locally.
    '''
    if opts.replicate:
        if data is None:
            data = read_url_data(response)
        dirpath = os.path.dirname(outpath)
        if os.path.exists(dirpath) is False:
            os.makedirs(dirpath)
        with open(outpath, 'wb') as ofp:
            ofp.write(data)
    return data


def is_html(info):
    '''
    Is this page an HTML page?
    '''
    content_type = 'None'
    if 'Content-Type' in info:
        content_type = info['Content-Type']
        if content_type.lower().find('html') >= 0:
            return True
    return False


def walk(url, opts, dups, depth=0, recurse=True, parent=None):
    '''
    Display the current page and continue walking over the web tree.
    '''
    url = clean_url(url)
    if proceed(url, opts, dups, depth) is False:
        return

    response = openurl(url, opts)
    if response is None:
        return

    info = response.info()
    data = None

    if display(url, opts):
        outpath = replicate_outpath(url, opts)
        data = report(url, opts, response, info, outpath, depth, parent)
        data = replicate(url, opts, response, data, outpath)

    if is_html(info) and recurse is True:
        html = read_url_data(response) if data is None else data
        parser = MyHtmlParser()
        parser.analyze(url, html)  # populate m_list
        for newurl in parser.m_list:
            recurse = newurl.startswith(url)  # skip external URLs
            walk(newurl, opts, dups, depth+1, recurse=recurse, parent=url)


def regex_compile(opts):
    '''
    Compile the regexs in the command line options for speed.
    '''
    if opts.exclude:
        setattr(opts, 'exclude_compiled', [])
        for pattern in opts.exclude:
            regex = re.compile(pattern)
            opts.exclude_compiled.append(regex)

    if opts.include:
        setattr(opts, 'include_compiled', [])
        for pattern in opts.include:
            regex = re.compile(pattern)
            opts.include_compiled.append(regex)

    if opts.filter:
        setattr(opts, 'filter_compiled', [])
        for pattern in opts.filter:
            regex = re.compile(pattern)
            opts.filter_compiled.append(regex)


def getopts():
    '''
    Get command line options.
    '''
    base = os.path.basename(sys.argv[0])
    def usage():
        'usage'
        usage = '{0} [OPTIONS] URL'.format(base)
        return usage
    def epilog():
        'epilogue'
        epilog = r'''
examples:
  $ # Example 1. Help
  $ {0} -h
  $ {0} --help

  $ # Example 2. Walk a HTTP site
  $ {0} http://internal.example.com

  $ # Example 3. Walk a HTTP site, show the page sizes
  $ {0} -v http://internal.example.com

  $ # Example 4. Walk a HTTP site, show the page sizes and types
  $ {0} -v -v http://internal.example.com

  $ # Example 5. Walk a HTTP site, show the page sizes, only display 2 levels
  $ {0} -m 2 -v http://internal.example.com

  $ # Example 6. Walk a HTTPS site
  $ #            Look at the -p and -P options if you do not want to
  $ #            be prompted for the user password.
  $ {0} -u username https://example.com
  Password for username?

  $ # Example 7. Exclude URLs that contain /tmp/
  $ {0} -e '/tmp/' http://example.com

  $ # Example 8. Only report the ".txt" files
  $ {0} -f '\.txt$' http://example.com

  $ # Example 9. Replicate the ".txt" files locally
  $ mkdir /tmp/mirror
  $ {0} -f '\.txt$' -r /tmp/mirror http://example.com

  $ # Example 10. Replicate all files locally
  $ mkdir /tmp/mirror
  $ {0} -v -r /tmp/mirror http://example.com
  $ tree /tmp/mirror  # see whats there

  $ # Example 11. Replicate "index.html" files locally
  $ #             This is a special case because the "index.html"
  $ #             is implied.
  $ mkdir /tmp/mirror
  $ {0} -f 'index\\.html$' -v -r /tmp/mirror http://example.com

  $ # Example 12. Print a hierarchical port using relative url paths.
  $ #             You can change the spacing with the -s option.
  $ {0} -I --R http://example.com
 '''.format(base)
        return epilog

    # Trick to capitalize the built-in headers.
    # Unfortunately I can't get rid of the ":" reliably.
    def gettext(s):
        lookup = {
            'show this help message and exit': 'Show this help message and exit.\n ',
        }
        return lookup.get(s, s)

    argparse._ = gettext  # to capitalize help headers
    afc = argparse.RawTextHelpFormatter
    desc = 'description:{0}'.format('\n  '.join(__doc__.split('\n')))
    parser = argparse.ArgumentParser(formatter_class=afc,
                                     description=desc[:-2],
                                     usage=usage(),
                                     epilog=epilog())

    parser.add_argument('-d', '--depth',
                        action='store',
                        type=int,
                        default=0,
                        metavar=('INT'),
                        help='''The maximum depth to search.
The default is no maximum.
 ''')

    parser.add_argument('-e', '--exclude',
                        action='append',
                        type=str,
                        help='''Exclude URLs that match these regex patterns.
It affects the search algorithm.
An example would be "-e '/../'" if you wanted to exclude URLs that redirected.
 ''')

    parser.add_argument('-f', '--filter',
                        action='append',
                        type=str,
                        help='''Only display results that match the regex patterns.
This is used to limit what is displayed or mirrored.
It does not affect the search algorithm.
An example would be "-i '*.js$'" if you only wanted to see the javascript files.
By default all results are displayed.
 ''')

    parser.add_argument('-i', '--include',
                        action='append',
                        type=str,
                        help='''Only include URLs that match these regex patterns.
It affects the search algorithm.
Use this option carefully.
 ''')

    parser.add_argument('-I', '--indent',
                        action='store_true',
                        help='''Alter the reporting to indent the URLs based on their
location in the page hierarchy.
The default is to not indent.
Use -s to change the number of spaces to indent per level.
Indenting does not work very well with filters because the parents
are typically filtered out.
 ''')
    
    parser.add_argument('-n', '--no-warnings',
                        action='store_true',
                        help='''Disable warnings.
 ''')

    parser.add_argument('-p', '--password-file',
                        action='store',
                        type=str,
                        metavar=('FILE'),
                        help='''A file that contains the password.
 ''')
    
    parser.add_argument('-P', '--password',
                        action='store',
                        type=str,
                        metavar=('FILE'),
                        help='''The password.
This should only be used in a script with 0700
permissions because command line arguments can
be seen in the shell history.
 ''')
    
    parser.add_argument('-r', '--replicate',
                        action='store',
                        type=str,
                        metavar=('DIR'),
                        help='''Replicate the contents locally in DIR.
The default is to not replicate.
 ''')

    parser.add_argument('-R', '--relurl',
                        action='store_true',
                        help='''Use the relative path for the url.
This is typically only useful when used in indentation mode but
even then it may produce odd output if there are many URLs to
external sites.
 ''')

    parser.add_argument('-s', '--spaces-per-indent',
                        action='store',
                        type=int,
                        default=3,
                        metavar=('INT'),
                        help='''The number of spaces to indent per level if -I is specified.
If -I is not specified, this option is ignored.
The default is %(default)s.
 ''')
    
    parser.add_argument('-u', '--username',
                        action='store',
                        type=str,
                        help='''The user name to use for authentication.
If no password option like -p or -P is specified, the user
is prompted for the password.
 ''')
    
    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='''Increase the level of verbosity.
      -v  Show the content-length.
   -v -v  Show the content-length and the content-type.
-v -v -v  Show the content-length, the content-type and the header.
 ''')

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s v{0}'.format(VERSION))

    parser.add_argument('URL',
                        action='store',
                        help='The URL to search.')

    opts = parser.parse_args()

    # utility for reporting errors
    def err(msg):
        sys.stderr.write('ERROR: {}\n'.format(msg))
        sys.exit(1)
        
    # Handle the user name and password data.
    # If the user specified a username, then we need to get the
    # associated password.
    # Once we have the user name and password, create the authenticate
    # attribute on the opts object.
    username = opts.username
    password = None
    if opts.password and opts.password_file:
        err('the arguments --password (-P) and --password-file (-P) are mutually exclusive')
    if opts.password:
        password = opts.password
    if opts.password_file:
        if os.path.exists(opts.password_file) is False:
            err('password file does not exist: {}'.format(opts.password_file))
        with open(opts.password_file, 'r') as ifp:
            password = ifp.read().strip()
    if password and username is None:
        err('username must be specified when a password is specified')
    if password is None and username:
        password = getpass.getpass('Password for {}? '.format(username))
    if password and username:
        setattr(opts, 'authenticate', (username, password))
    else:
        setattr(opts, 'authenticate', None)

    # Handle replication.
    if opts.replicate:
        if os.path.exists(opts.replicate) is False:
            err('replication directory does not exist: {}'.format(opts.replicate))

    return opts


def main():
    '''
    Main
    '''
    opts = getopts()
    dups = {}
    url = opts.URL
    try:
        regex_compile(opts)
        walk(url, opts, dups)
    except KeyboardInterrupt:
        sys.stderr.write('\n^C interrupt\n')
        sys.exit(1)


if __name__ == '__main__':
    main()