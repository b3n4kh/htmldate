Evaluation
==========


Although text is ubiquitous on the Web, extracting information from web pages can prove to be difficult. The following evaluation features out-of-the-box solutions for Python.


Tested solutions
----------------

- `articleDateExtractor <https://github.com/Webhose/article-date-extractor>`_ detects, extracts and normalizes the publication date of an online article or blog post,
- `date_guesser <https://github.com/mitmedialab/date_guesser>`_ extracts publication dates from a web pages along with an accuracy measure (not used here),
- `goose3 <https://github.com/goose3/goose3>`_ can extract information for embedded content,
- `htmldate <https://github.com/adbar/htmldate>`_ is the software package described here, it is designed to extract original and updated publication dates of web pages,
- `newspaper3k <https://github.com/codelucas/newspaper>`_ is mostly geared towards newspaper texts,
- `news-please <https://github.com/fhamborg/news-please>`_ is a news crawler that extracts structured information,




Description
-----------

**Test set**: the experiments below are run on a collection of documents which are either typical for Internet articles (news outlets, blogs, including smaller ones) or randomly selected from `large collections of web pages in German <https://www.dwds.de/d/k-web>`_. For the sake of completeness a few documents in other languages were added (mostly in English and French but also in Finnish and Chinese for example).

**Evaluation**: only documents with dates that are clearly to be determined are considered for this benchmark. A given day is taken as unit of reference, meaning that results are converted to ``%Y-%m-%d`` format if necessary in order to make them comparable. The evaluation script is available on the project repository: `tests/comparison.py <https://github.com/adbar/htmldate/blob/master/tests/comparison.py>`_. To reproduce the tests just clone the repository, install all necessary packages and run the evaluation script with the data provided in the *tests* directory.

**Time**: the execution time (best of 3 tests) cannot be easily compared in all cases as some solutions perform a whole series of operations which are irrelevant to this task. However, *htmldate* is noticeably faster than the strictly comparable packages (*articleDateExtractor* and most certainly *date_guesser*).

**Errors:** *goose3*'s output isn't always meaningful and/or in a standardized format, these cases were discarded. *news-please* seems to have trouble with some encodings (e.g. in Chinese), in which case it leads to an exception.


Results
-------

The results below show that **date extraction is not a completely solved task** but one for which extractors have to resort to heuristics and guesses. The figures documenting recall and accuracy capture the real-world performance of the tools as the absence of a date output impacts the result.


=============================== ========= ========= ========= ========= =======
200 web pages containing identifiable dates (2020-03-04)
-------------------------------------------------------------------------------
Python Package                  Precision Recall    Accuracy  F-Score   Time
=============================== ========= ========= ========= ========= =======
newspaper3k 0.2.8               **0.917** 0.399     0.385     0.556     78.6
goose3 3.1.6                    0.910     0.422     0.405     0.577     13.5
date_guesser 2.1.4              0.825     0.553     0.495     0.662     36.7
news-please 1.4.25              0.831     0.638     0.565     0.722     64.5
articleDateExtractor 0.20       0.832     0.644     0.570     0.726     5.7
htmldate 0.6.1 (fast)           **0.917** 0.897     0.830     0.907     **2.2**
htmldate[all] 0.6.1 (extensive) 0.899     **0.994** **0.895** **0.945** 5.4
=============================== ========= ========= ========= ========= =======


Precision describes if the dates given as output are correct: *newspaper3k* and *goose3* fare well precision-wise but they fail to extract dates in a large majority of cases (poor recall). The difference in accuracy between *date_guesser* and *newspaper3k* is consistent with tests described on the `website of the former <https://github.com/mitmedialab/date_guesser>`_.

It turns out that *htmldate* performs better than the other solutions overall. Most of all and despite being measured on a sample, **the higher accuracy and faster processing time are highly significant**. Especially for smaller news outlets, websites and blogs, as well as pages written in languages other than English (in this case mostly but not exclusively German), *htmldate* greatly extends date extraction coverage without sacrificing precision.


Note on the different versions:

- *htmldate[all]* means that additional components are added for performance and coverage, which results in differences with respect to accuracy (due to further linguistic analysis) and potentially speed (faster date parsing). They can be installed with ``pip/pip3/pipenv htmldate[all]``.
- The fast mode does not output as many dates (lower recall) but its guesses are more often correct (better precision).