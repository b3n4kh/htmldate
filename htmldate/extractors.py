# pylint:disable-msg=E0611,I1101
"""
Custom parsers and XPath expressions for date extraction
"""

## This file is available from https://github.com/adbar/htmldate
## under GNU GPL v3 license

# standard
import datetime
import logging
import re

from functools import lru_cache

from dateutil.parser import parse as dateutil_parse

# coverage for date parsing
from dateparser import DateDataParser  # third-party, slow
from dateparser_data.settings import default_parsers

# own
from .settings import CACHE_SIZE
from .validators import convert_date, date_validator


LOGGER = logging.getLogger(__name__)

EXTERNAL_PARSER = DateDataParser(settings={
#    'DATE_ORDER': 'DMY',
    'PREFER_DATES_FROM': 'past',
#    'PREFER_DAY_OF_MONTH': 'first',
    'STRICT_PARSING': True,
    'PARSERS': [p for p in default_parsers if p not in ('no-spaces-time', 'relative-time', 'timestamp')],
})


FAST_PREPEND = './/*[(self::b or self::div or self::em or self::font or self::i or self::li or self::p or self::span or self::strong)]'
SLOW_PREPEND = './/*'
DATE_EXPRESSIONS = """
    [contains(translate(@id, "D", "d"), 'date')
    or contains(translate(@class, "D", "d"), 'date')
    or contains(translate(@itemprop, "D", "d"), 'date')
    or contains(translate(@id, "D", "d"), 'datum')
    or contains(translate(@class, "D", "d"), 'datum')
    or contains(@id, 'time') or contains(@class, 'time')
    or @class='meta' or contains(translate(@id, "M", "m"), 'metadata')
    or contains(translate(@class, "M", "m"), 'meta-')
    or contains(translate(@class, "M", "m"), '-meta')
    or contains(translate(@id, "M", "m"), '-meta')
    or contains(translate(@class, "M", "m"), '_meta')
    or contains(translate(@class, "M", "m"), 'postmeta')
    or contains(@class, 'info') or contains(@class, 'post_detail')
    or contains(@class, 'block-content')
    or contains(@class, 'byline') or contains(@class, 'subline')
    or contains(@class, 'posted') or contains(@class, 'submitted')
    or contains(@class, 'created-post')
    or contains(@id, 'publish') or contains(@class, 'publish')
    or contains(@class, 'publication')
    or contains(@class, 'author') or contains(@class, 'autor')
    or contains(@class, 'field-content')
    or contains(@class, 'fa-clock-o') or contains(@class, 'fa-calendar')
    or contains(@class, 'fecha') or contains(@class, 'parution')
    or contains(@class, 'footer') or contains(@id, 'footer')]
    |
    .//footer|.//small
    """
# further tests needed:
# or contains(@class, 'article')
# or contains(@id, 'lastmod') or contains(@class, 'updated')

FREE_TEXT_EXPRESSIONS = FAST_PREPEND + '/text()'

# discard parts of the webpage
# archive.org banner inserts
DISCARD_EXPRESSIONS = """.//div[@id="wm-ipp-base" or @id="wm-ipp"]"""
# not discarded for consistency (see above):
# .//footer
# .//*[(self::div or self::section)][@id="footer" or @class="footer"]

# regex cache
YMD_NO_SEP_PATTERN = re.compile(r'(?:\D|^)(\d{8})(?:\D|$)')
YMD_PATTERN = re.compile(r'(?:\D|^)(\d{4})[\-/.](\d{1,2})[\-/.](\d{1,2})(?:\D|$)')
DMY_PATTERN = re.compile(r'(?:\D|^)(\d{1,2})[\-/.](\d{1,2})[\-/.](\d{2,4})(?:\D|$)')
YM_PATTERN = re.compile(r'(?:\D|^)(\d{4})[\-/.](\d{1,2})(?:\D|$)')
MY_PATTERN = re.compile(r'(?:\D|^)(\d{1,2})[\-/.](\d{4})(?:\D|$)')

REGEX_MONTHS = '''
January|February|March|April|May|June|July|August|September|October|November|December|
Januari|Februari|Maret|Mei|Juni|Juli|Agustus|Oktober|Desember|
Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec|
Januar|Jänner|Februar|Feber|März|Mai|Dezember|
janvier|février|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|décembre|
Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık|
Oca|Şub|Mar|Nis|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara
'''  # "août" hurts performance?
LONG_MDY_PATTERN = re.compile(fr'''({REGEX_MONTHS})\s
([0-9]{{1,2}})(?:st|nd|rd|th)?,? ([0-9]{{4}})'''.replace('\n', ''), re.I)
LONG_DMY_PATTERN = re.compile(fr'''([0-9]{{1,2}})(?:st|nd|rd|th|\.)? (?:of )?
({REGEX_MONTHS}),? ([0-9]{{4}})'''.replace('\n', ''), re.I)

COMPLETE_URL = re.compile(r'([0-9]{4})[/-]([0-9]{1,2})[/-]([0-9]{1,2})')
PARTIAL_URL = re.compile(r'/([0-9]{4})/([0-9]{1,2})/')

JSON_MODIFIED = re.compile(r'"dateModified": ?"([0-9]{4}-[0-9]{2}-[0-9]{2})', re.I)
JSON_PUBLISHED = re.compile(r'"datePublished": ?"([0-9]{4}-[0-9]{2}-[0-9]{2})', re.I)
TIMESTAMP_PATTERN = re.compile(r'([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{2}\.[0-9]{2}\.[0-9]{4}).[0-9]{2}:[0-9]{2}:[0-9]{2}')

# English, French, German, Indonesian and Turkish dates cache
TEXT_MONTHS = {
    # January
    'januar': '01', 'jänner': '01', 'january': '01', 'januari': '01', 'jan': '01',
    'ocak': '01', 'oca': '01', 'janvier': '01',
    # February
    'februar': '02', 'feber': '02', 'february': '02', 'februari': '02', 'feb': '02',
    'şubat': '02', 'şub': '02', 'février': '02',
    # March
    'märz': '03', 'march': '03', 'maret': '03', 'mar': '03', 'mart': '03', 'mars': '03',
    # April
    'april': '04', 'apr': '04', 'nisan': '04', 'nis': '04', 'avril': '04',
    # May
    'mai': '05', 'may': '05', 'mei': '05', 'mayıs': '05',
    # June
    'juni': '06', 'june': '06', 'jun': '06', 'haziran': '06', 'haz': '06', 'juin': '06',
    # July
    'juli': '07', 'july': '07', 'jul': '07', 'temmuz': '07', 'tem': '07', 'juillet': '07',
    # August
    'august': '08', 'agustus': '08', 'aug': '08', 'ağustos': '08', 'ağu': '08',
    'août': '08', 'aout': '08',
    # September
    'september': '09', 'sep': '09', 'eylül': '09', 'eyl': '09', 'septembre': '09',
    # October
    'oktober': '10', 'october': '10', 'oct': '10', 'ekim': '10', 'eki': '10', 'octobre': '10',
    # November
    'november': '11', 'nov': '11', 'kasım': '11', 'kas': '11', 'novembre': '11',
    # December
    'dezember': '12', 'december': '12', 'desember': '12', 'dec': '12', 'aralık': '12',
    'ara': '12', 'décembre': '12'
}

TEXT_DATE_PATTERN = re.compile(r'[.:,_/ -]|^[0-9]+$')
NO_TEXT_DATE_PATTERN = re.compile(r'[0-9]{3,}\D+[0-9]{3,}|[0-9]{2}:[0-9]{2}(:| )|\+[0-9]{2}\D+|\D*[0-9]{4}\D*$')
# leads to errors: \D+[0-9]{3,}\D+|

# use of regex module for speed
EN_PATTERNS = re.compile(r'(?:date[^0-9"]{,20}|updated|published) *?(?:in)? *?:? *?([0-9]{1,4})[./]([0-9]{1,2})[./]([0-9]{2,4})', re.I)
DE_PATTERNS = re.compile(r'(?:Datum|Stand): ?([0-9]{1,2})\.([0-9]{1,2})\.([0-9]{2,4})', re.I)
TR_PATTERNS = re.compile(r'''(?:güncellen?me|yayı(?:m|n)lan?ma) *?(?:tarihi)? *?:? *?([0-9]{1,2})[./]([0-9]{1,2})[./]([0-9]{2,4})|
([0-9]{1,2})[./]([0-9]{1,2})[./]([0-9]{2,4}) *?(?:'de|'da|'te|'ta|’de|’da|’te|’ta|tarihinde) *(?:güncellendi|yayı(?:m|n)landı)'''.replace('\n', ''), re.I)

# core patterns
THREE_COMP_REGEX_A = re.compile(r'([0-3]?[0-9])[/.-]([01]?[0-9])[/.-]([0-9]{4})')
THREE_COMP_REGEX_B = re.compile(r'([0-3]?[0-9])[/.-]([01]?[0-9])[/.-]([0-9]{2})')
TWO_COMP_REGEX = re.compile(r'([0-3]?[0-9])[/.-]([0-9]{4})')

# extensive search patterns
YEAR_PATTERN = re.compile(r'^\D?(199[0-9]|20[0-9]{2})')
COPYRIGHT_PATTERN = re.compile(r'(?:©|\&copy;|Copyright|\(c\))\D*(?:[12][0-9]{3}-)?([12][0-9]{3})\D')
THREE_PATTERN = re.compile(r'/([0-9]{4}/[0-9]{2}/[0-9]{2})[01/]')
THREE_CATCH = re.compile(r'([0-9]{4})/([0-9]{2})/([0-9]{2})')
THREE_LOOSE_PATTERN = re.compile(r'\D([0-9]{4}[/.-][0-9]{2}[/.-][0-9]{2})\D')
THREE_LOOSE_CATCH = re.compile(r'([0-9]{4})[/.-]([0-9]{2})[/.-]([0-9]{2})')
SELECT_YMD_PATTERN = re.compile(r'\D([0-3]?[0-9][/.-][01]?[0-9][/.-][0-9]{4})\D')
SELECT_YMD_YEAR = re.compile(r'(19[0-9]{2}|20[0-9]{2})\D?$')
YMD_YEAR = re.compile(r'^([0-9]{4})')
DATESTRINGS_PATTERN = re.compile(r'(\D19[0-9]{2}[01][0-9][0-3][0-9]\D|\D20[0-9]{2}[01][0-9][0-3][0-9]\D)')
DATESTRINGS_CATCH = re.compile(r'([12][0-9]{3})([01][0-9])([0-3][0-9])')
SLASHES_PATTERN = re.compile(r'\D([0-3]?[0-9][/.][01]?[0-9][/.][0129][0-9])\D')
SLASHES_YEAR = re.compile(r'([0-9]{2})$')
YYYYMM_PATTERN = re.compile(r'\D([12][0-9]{3}[/.-][01][0-9])\D')
YYYYMM_CATCH = re.compile(r'([12][0-9]{3})[/.-]([01][0-9])')
MMYYYY_PATTERN = re.compile(r'\D([01]?[0-9][/.-][12][0-9]{3})\D')
MMYYYY_YEAR = re.compile(r'([12][0-9]{3})\D?$')
SIMPLE_PATTERN = re.compile(r'\D(199[0-9]|20[0-9]{2})\D')


def discard_unwanted(tree):
    '''Delete unwanted sections of an HTML document and return them as a list'''
    my_discarded = []
    for subtree in tree.xpath(DISCARD_EXPRESSIONS):
        my_discarded.append(subtree)
        subtree.getparent().remove(subtree)
    return tree, my_discarded


def extract_url_date(testurl, outputformat):
    """Extract the date out of an URL string complying with the Y-M-D format"""
    match = COMPLETE_URL.search(testurl)
    if match:
        dateresult = match.group(0)
        LOGGER.debug('found date in URL: %s', dateresult)
        try:
            dateobject = datetime.datetime(int(match.group(1)),
                                           int(match.group(2)),
                                           int(match.group(3)))
            if date_validator(dateobject, outputformat) is True:
                return dateobject.strftime(outputformat)
        except ValueError as err:
            LOGGER.debug('conversion error: %s %s', dateresult, err)
    return None


def extract_partial_url_date(testurl, outputformat):
    """Extract an approximate date out of an URL string in Y-M format"""
    match = PARTIAL_URL.search(testurl)
    if match:
        dateresult = match.group(0) + '/01'
        LOGGER.debug('found partial date in URL: %s', dateresult)
        try:
            dateobject = datetime.datetime(int(match.group(1)),
                                           int(match.group(2)),
                                           1)
            if date_validator(dateobject, outputformat) is True:
                return dateobject.strftime(outputformat)
        except ValueError as err:
            LOGGER.debug('conversion error: %s %s', dateresult, err)
    return None


def correct_year(year):
    """Adapt year from YY to YYYY format"""
    if year < 100:
        year += 1900 if year >= 90 else 2000
    return year


def try_swap_values(day, month):
    """Swap day and month values if it seems feaaible."""
    # If month is more than 12, swap it with the day
    if month > 12 and day <= 12:
        day, month = month, day
    return day, month


def regex_parse(string):
    """Try full-text parse for date elements using a series of regular expressions
       with particular emphasis on English, French, German and Turkish"""
    # https://github.com/vi3k6i5/flashtext ?
    # multilingual day-month-year pattern
    match = LONG_DMY_PATTERN.search(string)
    if match:
        day, month, year = match.group(1), TEXT_MONTHS[match.group(2).lower()], match.group(3)
    else:
        # American English
        match = LONG_MDY_PATTERN.search(string)
        if match:
            day, month, year = match.group(2), TEXT_MONTHS[match.group(1).lower()], match.group(3)
        else:
            return None
    # process and return
    try:
        int_day, int_month, int_year = int(day), int(month), int(year)
        int_year = correct_year(int_year)
        int_day, int_month = try_swap_values(int_day, int_month)
        dateobject = datetime.date(int_year, int_month, int_day)
    except ValueError:
        return None
    else:
        LOGGER.debug('multilingual text found: %s', dateobject)
        return dateobject


# TODO: check what's necessary here and what's not
def custom_parse(string, outputformat, min_date, max_date):
    """Try to bypass the slow dateparser"""
    LOGGER.debug('custom parse test: %s', string)

    # 1. '201709011234' not covered by dateparser, and regex too slow
    if string[:8].isdigit():
        try:
            candidate = datetime.date(int(string[:4]),
                                      int(string[4:6]),
                                      int(string[6:8]))
        except ValueError:
            return None
        if date_validator(candidate, '%Y-%m-%d') is True:
            LOGGER.debug('ymd match: %s', candidate)
            return convert_date(candidate, '%Y-%m-%d', outputformat)

    # 2. shortcut, much faster
    if string[:4].isdigit():
        try:
            result = dateutil_parse(string, fuzzy=False)  # ignoretz=True
            if date_validator(result, outputformat, earliest=min_date, latest=max_date) is True:
                LOGGER.debug('parsing result: %s', result)
                return result.strftime(outputformat)
        except (OverflowError, TypeError, ValueError):
            LOGGER.debug('parsing error: %s', string)

    # 3. Try YYYYMMDD, use regex
    match = YMD_NO_SEP_PATTERN.search(string)
    if match:
        try:
            year, month, day = int(match.group(1)[:4]), int(match.group(1)[4:6]), int(match.group(1)[6:8])
            candidate = datetime.date(year, month, day)
        except ValueError:
            LOGGER.debug('YYYYMMDD value error: %s', match.group(0))
        else:
            if date_validator(candidate, '%Y-%m-%d') is True:
                LOGGER.debug('YYYYMMDD match: %s', candidate)
                return convert_date(candidate, '%Y-%m-%d', outputformat)

    # 4. Try Y-M-D pattern since it's the one used in ISO-8601
    # see also fromisoformat() in Python >= 3.7
    match = YMD_PATTERN.search(string)
    if match:
        try:
            day, month, year = int(match.group(3)), int(match.group(2)), int(match.group(1))
            candidate = datetime.date(year, month, day)
        except ValueError:
            LOGGER.debug('Y-M-D value error: %s', match.group(0))
        else:
            if date_validator(candidate, '%Y-%m-%d') is True:
                LOGGER.debug('Y-M-D match: %s', candidate)
                return convert_date(candidate, '%Y-%m-%d', outputformat)

    # 5. Try the D-M-Y pattern since it's the most common date format in the world
    match = DMY_PATTERN.search(string)
    if match:
        try:
            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            year = correct_year(year)
            day, month = try_swap_values(day, month)
            candidate = datetime.date(year, month, day)
        except ValueError:
            LOGGER.debug('D-M-Y value error: %s', match.group(0))
        else:
            if date_validator(candidate, '%Y-%m-%d') is True:
                LOGGER.debug('D-M-Y match: %s', candidate)
                return convert_date(candidate, '%Y-%m-%d', outputformat)

    # 6. Try the Y-M pattern
    match = YM_PATTERN.search(string)
    if match:
        try:
            year, month = int(match.group(1)), int(match.group(2))
            candidate = datetime.date(year, month, 1)
        except ValueError:
            LOGGER.debug('Y-M value error: %s', match.group(0))
        else:
            if date_validator(candidate, '%Y-%m-%d') is True:
                LOGGER.debug('Y-M match: %s', candidate)
                return convert_date(candidate, '%Y-%m-%d', outputformat)

    # 7. Try the other regex pattern
    dateobject = regex_parse(string)
    if date_validator(dateobject, outputformat) is True:
        try:
            LOGGER.debug('custom parse result: %s', dateobject)
            return dateobject.strftime(outputformat)
        except ValueError as err:
            LOGGER.error('value error during conversion: %s %s', string, err)

    return None


def external_date_parser(string, outputformat):
    """Use dateutil parser or dateparser module according to system settings"""
    LOGGER.debug('send to external parser: %s', string)
    try:
        target = EXTERNAL_PARSER.get_date_data(string)['date_obj']
    # 2 types of errors possible
    except (OverflowError, ValueError) as err:
        target = None
        LOGGER.error('external parser error: %s %s', string, err)
    # issue with data type
    if target is not None:
        return datetime.date.strftime(target, outputformat)
    return None


@lru_cache(maxsize=CACHE_SIZE)
def try_ymd_date(string, outputformat, extensive_search, min_date, max_date):
    """Use a series of heuristics and rules to parse a potential date expression"""
    # if string less than 6 chars, stop
    if not string or len(string) < 6:
        return None

    # count how many digit number in this string
    if not 4 <= len([c for c in string if c.isdigit()]) <= 18:
        return None

    # check if string only contains time/single year or digits and not a date
    if not TEXT_DATE_PATTERN.search(string) or NO_TEXT_DATE_PATTERN.match(string):
        return None

    # try to parse using the faster method
    customresult = custom_parse(string, outputformat, min_date, max_date)
    if customresult is not None:
        return customresult

    # use slow but extensive search
    if extensive_search is True:
        # send to date parser
        dateparser_result = external_date_parser(string, outputformat)
        if date_validator(
            dateparser_result, outputformat, earliest=min_date, latest=max_date
        ):
            return dateparser_result

    return None


def img_search(tree, outputformat, min_date, max_date):
    '''Skim through image elements'''
    element = tree.find('.//meta[@property="og:image"]')
    if element is not None and 'content' in element.attrib:
        result = extract_url_date(element.get('content'), outputformat)
        if date_validator(result, outputformat, earliest=min_date, latest=max_date) is True:
            return result
    return None


def json_search(tree, outputformat, original_date, min_date, max_date):
    '''Look for JSON time patterns in JSON sections of the tree'''
    # determine pattern
    if original_date is True:
        json_pattern = JSON_PUBLISHED
    else:
        json_pattern = JSON_MODIFIED
    # look throughout the HTML tree
    for elem in tree.xpath('.//script[@type="application/ld+json"]|//script[@type="application/settings+json"]'):
        if not elem.text or '"date' not in elem.text:
            continue
        json_match = json_pattern.search(elem.text)
        if json_match and date_validator(json_match.group(1), '%Y-%m-%d', earliest=min_date, latest=max_date):
            LOGGER.debug('JSON time found: %s', json_match.group(0))
            return convert_date(json_match.group(1), '%Y-%m-%d', outputformat)
    return None


def timestamp_search(htmlstring, outputformat, min_date, max_date):
    '''Look for timestamps throughout the web page'''
    tstamp_match = TIMESTAMP_PATTERN.search(htmlstring)
    if tstamp_match and date_validator(tstamp_match.group(1), '%Y-%m-%d', earliest=min_date, latest=max_date):
        LOGGER.debug('time regex found: %s', tstamp_match.group(0))
        return convert_date(tstamp_match.group(1), '%Y-%m-%d', outputformat)
    return None


def extract_idiosyncrasy(idiosyncrasy, htmlstring, outputformat, min_date, max_date):
    '''Look for a precise pattern throughout the web page'''
    candidate = None
    match = idiosyncrasy.search(htmlstring)
    groups = [0, 1, 2, 3] if match and match.group(3) else []  #because len(None) has no len
    try:
        groups = [0, 4, 5, 6] if match and match.group(6) else groups
    except IndexError:
        pass
    if match and groups:
        if match.group(groups[1]) is not None and len(match.group(groups[1])) == 4:
            candidate = datetime.date(int(match.group(groups[1])),
                                      int(match.group(groups[2])),
                                      int(match.group(groups[3])))
        elif len(match.group(groups[3])) in (2, 4):
            # DD/MM/YY
            day, month = try_swap_values(int(match.group(groups[1])), int(match.group(groups[2])))
            year = correct_year(int(match.group(groups[3])))
            try:
                candidate = datetime.date(year, month, day)
            except ValueError:
                LOGGER.debug('value error in idiosyncrasies: %s', match.group(0))
    if date_validator(candidate, '%Y-%m-%d', earliest=min_date, latest=max_date) is True:
        LOGGER.debug('idiosyncratic pattern found: %s', match.group(0))
        return convert_date(candidate, '%Y-%m-%d', outputformat)
    return None


def idiosyncrasies_search(htmlstring, outputformat, min_date, max_date):
    '''Look for author-written dates throughout the web page'''
    result = None
    # DE
    result = extract_idiosyncrasy(DE_PATTERNS, htmlstring, outputformat, min_date, max_date)
    # EN
    if result is None:
        result = extract_idiosyncrasy(EN_PATTERNS, htmlstring, outputformat, min_date, max_date)
    # TR
    if result is None:
        result = extract_idiosyncrasy(TR_PATTERNS, htmlstring, outputformat, min_date, max_date)
    return result
