## webwalk

Tool to recursively walk over the pages of a web site and display the links to
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
partial mirror based on the filtering. You even just copy over files.

It is useful for understanding how a web site is layed out or for
finding data files to download. It is also useful for understanding
how to use Python 2.7 and 3.x tools to process web sites.

## License
MIT open source
<br>Copyright (&copy;) Joe Linoff 2016

## Download
Here is how you download and install it.
```bash
$ git clone https://github.com/jlinoff/webwalk.git
$ cp webwalk/webwalk.py <release_dir>/
$ webwalk.py -h
```
## Examples
Here are some examples of how you might use it.

#### Example 1: Get help
```bash
$ webwalk.py --help
```

#### Example 2: Analyze site
```bash
$ webwalk.py -v http://example.com/
```
Used -v to see the file sizes.

#### Example 3: Analyze a site with indented output
```bash
$ webwalk.py -I -R http://example.com/
```

#### Example 4: Analyze an HTTPS site
```bash
$ webwalk.py -u me123 https://secure.example.com/
Password for me123?
```

#### Example 5: Find all of the '.js' files.
```bash
$ webwalk.py -f '\\.js$' http://example.com/

$ # Another option.
$ webwalk.py http://example.com 2>&1 | tee example.com.log
$ grep '\.js$' example.com.log
```

#### Example 6: Replicate a site
```bash
$ mkdir /tmp/work.example.com
$ webwalk.py -r /tmp/work.example.com -e '/tmp/' -e '/../' http://work.example.com/
```
Note that we are ignoring paths with `/tmp/` and `/../` in them.

#### Example 7: Copy over tar.bz2 archive files from a site
```bash
$ mkdir /tmp/archives
$ webwalk.py -c /tmp/archives -e '/tmp/' -e '/.../' -f '\.tar.bz2' http://work.example.com/downloads/
```

## Options
This is a brief summary of the options available. Use -h to get more details.

| Short       | Long                      | Description   |
| ----------- | ------------------------- | ------------- |
| -c [DIR]    | --copy [DIR]              | Copy all filtered files to a single directory. The directory must exist. |
|             | --debug                   | Added debug function for development. |
| -d [INT]    | --depth [INT]             | The maximum depth to search. The default is no maximum. |
| -e [REGEX]  | --exclude [REGEX]         | Exclude pages that match the REGEX pattern. This affects the search algorithm. This option be specified multiple times. |
| -f [REGEX]  | --filter [REGEX]          | Only report the results that match the REGEX pattern. This does not affect the search algorithm. This option be specified multiple times. |
| -h          | --help                    | Help message. |
| -i [REGEX]  | --include [REGEX]         | Only include pages that match the REGEX pattern. This affects the search algorithm so it must be used carefully. This option be specified multiple times. |
| -I          | --indent                  | Alter the reporting to ident the URLs based on their location in the page hierarchy. |
| -n          | --no-warnings             | Disable warning messages. |
| -p [FILE]   | --password-file [FILE]    | File that contains the user password for HTTPS sites. |
| -P&nbsp;[STRING] | --password [STRING]       | Plaintext password on the command line. Best used in a protected script. |
| -r [DIR]    | --replicate [DIR]         | Replicate a site locally. This is slow, there are probably better options available. |
| -R          | --relurl                  | Use relative paths for the URLs. Not really interesting unless -I is specified. |
| -s [INT]    | --spaces-per-indent&nbsp;[INT] | The number of spaces to indent per level if -I is specified. |
| -u [NAME]   | --username [NAME]         | Username for accessing HTTPS web sites. If no password is specified, the user prompted. |
| -v          | --verbose                 | Increase the level of verbosity. |
| -V          | --version                 | Display the version number and exit. |

Enjoy!
