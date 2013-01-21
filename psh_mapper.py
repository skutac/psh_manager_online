import urllib2

from functions import query_to_dicts

def map_to_dbpedia(subject):
    subject = subject.capitalize()
    url = "http://dbpedia.org/page/%s"%subject
    try:
        dbpedia = urllib2.urlopen(url)
    except urllib2.HTTPError:
        url = False
    except Exception, e:
        print str(e)
        pass

    return url