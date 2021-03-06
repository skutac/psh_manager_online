# -*- coding: utf-8 -*-
"""
handler.py [-option]

Handler is module for updating PSH database in PSH Manager project and parts that are dependent on changes made in structure of PSH
(HTML navigation tree, representation of subjects stored in files).

OPTIONS

   -n -downloads only new records from server, cannot take care of changes made in structure of older subjects

   -a -iteratively updates each subject in database, it takes a long time but during the process the database is still prepared for use
"""

import os, sys, time, urllib2, math, re, datetime, csv

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_local'

from psh.models import Hesla, Varianta, Ekvivalence, Hierarchie, Topconcepts, Pribuznost, Zkratka, SysNumber, Aktualizace, Vazbywikipedia, Vazbydbpedia, PocetZaznamu

from functions import query_to_dicts

from django.conf import settings
from django.http import HttpResponse
from django.core.mail import send_mail
from django.core.exceptions import ObjectDoesNotExist

import psh_mapper

conceptTable = u"""
    <table>
    <tr>
    <td>
    <table>
    <tr>
    <td>
    <div id='titleCS'>%s<sup id="acronym">%s</sup></div>
    <div id='titleEN'>%s</div>
    <div id='pshID'>%s</div>
    </td>
    </tr>
    <tr>
    <td>
    <div class="title">Nepreferované znění [CS]</div>
    <ul id='nonprefCS'>%s</ul>
    </td>
    </tr>
    <tr>
    <td>
    <div class="title">Nepreferované znění [EN]</div>
    <ul id='nonprefEN'>%s</ul>
    </td>
    </tr>
    <tr>
    <td>
    <div class="title">Příbuzná hesla</div>
    <ul id='related'>%s</ul>
    </td>
    </tr>
    </table>
    </td>
    <td>
    <table>
    <tr>
    <td>
    <div class="title">Nadřazené heslo</div>
    <ul id="broader">%s</ul>
    </td>
    </tr>
    <tr>
    <td>
    <div class="title">Podřazená hesla</div>
    <ul id='narrower'>%s</ul>
    </td>
    </tr>
    </table>
    </td>
    </tr>
    </table>
    """

def createTree():
    """Creates PSH tree structure as navigation for left column of PSH Manager"""
    print "Making PSH tree structure..."
    concepts = []
    treeFile = open("".join([settings.ROOT, "/static/html/tree_temp.html"]), "w")
    topURI = Topconcepts.objects.all()
    if len(topURI) == 0:
        getTopConcepts()
        topURI = Topconcepts.objects.all()

    tree = []
    for uri in topURI:
        concept = Hesla.objects.get(id_heslo=uri.id_heslo)
        concepts.append(concept)
    concepts.sort(key=lambda x: x.heslo)

    for concept in concepts:
        print "---- Top concept:", concept.id_heslo, "----"
        tree.append("".join(['<li class="heslo unwrap" id="', concept.id_heslo, '">',  concept.heslo, '</li>\n']))
        chunk = getTree(concept.id_heslo)
        if chunk:
            tree.append(chunk)

    output = "".join(tree)
    treeFile.write(output.encode("utf8"))
    treeFile.close()
    os.system("rm %s/static/html/tree.html" %settings.ROOT)
    os.system("mv %s/static/html/tree_temp.html %s/static/html/tree.html" %(settings.ROOT, settings.ROOT))

def getTree(subjectID, level=1):
    """Gets part of the tree structure in proccess of creating main PSH navigation tree"""
    current = []
    hesla = []
    ids = Hierarchie.objects.filter(nadrazeny=subjectID)
    try:
        if len(ids) > 0:

            for id in ids:
                podrazeny = Hesla.objects.get(id_heslo=id.podrazeny)
                hesla.append(podrazeny)

            hesla.sort(key=lambda x: x.heslo.lower())

            for obj in hesla:
                if len(Hierarchie.objects.filter(nadrazeny=obj.id_heslo)):
                    current.append("".join(['<li class="heslo unwrap" id="', obj.id_heslo, '">',  obj.heslo, '</li>\n']))
                else:
                    current.append("".join(['<li class="heslo" id="', obj.id_heslo, '">',  obj.heslo, '</li>\n']))
                chunk = getTree(obj.id_heslo, level+1)

                if chunk:
                    current.append(chunk)

            ul_level = "".join(['level-', str(level)])
            return "".join(['<ul class="hidden ', ul_level, '">', "".join(current), '</ul>'])
        else:
            return False
    except Exception, e:
        print id, str(e)

def updatePSH(all):
    """Initiates update of PSH database. If parameter all == False, it downloads only new subjects from the server, if all == True, it updates each PSH subject in database form server"""

    print "Checking server for updates..."
    count = getRecordCount()
    print "".join(["Last PSH ID on server: ", str(count)])
    hesla = Hesla.objects.all()
    if all:
        print "Updating PSH database..."
        current_psh_ids = [heslo.id_heslo for heslo in hesla]
        last = 0
    else:
        try:
            nums = [int(heslo.id_heslo[3:]) for heslo in hesla if len(heslo.id_heslo) > 3]
            last = max(nums)
        except:
            last = 0
    print "".join(["Last PSH ID in database: ", str(last)])

    psh_ids = []
    if count > last:
        print "Updating database..."
        for num in range(last+1, count+1):
        #for num in range(1, 10):
            print "".join(["PSH", str(num), " GET"])
            subject = getSubject(num)
            if subject:
                deleteSubject(subject["id"])
                storeSubjectToDB(subject)
                translateLabel(subject["id"])
                psh_ids.append(subject["id"])

        translateLabels()
        createTree()
        make_skos()
        calculate_hierarchy_record_count()

    if all:
        psh_ids = set(psh_ids)
        current_psh_ids = set(current_psh_ids)
        to_remove = current_psh_ids - psh_ids
        if len(to_remove) < 10:
            for psh_id in to_remove:
                deleteSubject(psh_id)


def getSubject(num):
    """Gets record subject from server according to its number"""
    xml = urllib2.urlopen("".join(["http://aleph.techlib.cz/X?op=find_doc&base=STK10&doc_num=", str(num)])).read()
    if validSubject(xml):
        try:    
            id = re.search("<fixfield id=\"001\">(.*?)</fixfield>", xml).group(1)
            URI = "".join(["http://psh.ntkcz.cz/skos/", id])
            prefLabelCS = re.search("<varfield id=\"150\" i1=\" \" i2=\" \">(.*?)</varfield>", xml, re.S).group(1)
            acronym = re.search("<subfield label=\"x\">(.*?)</subfield>", prefLabelCS).group(1)
            prefLabelCS = re.search("<subfield label=\"a\">(.*?)</subfield>", prefLabelCS).group(1)
            prefLabelEN = re.search("<varfield id=\"750\" i1=\"0\" i2=\"7\">(.*?)</varfield>", xml, re.S).group(1)
            prefLabelEN = re.search("<subfield label=\"a\">(.*?)</subfield>", prefLabelEN).group(1)
            broader = re.search("<varfield id=\"550\" i1=\"9\" i2=\" \">(.*?)</varfield>", xml, re.S)
            if broader:
                broader = re.search("<subfield label=\"a\">(.*?)</subfield>", broader.group(1)).group(1)

            related = []
            for rel in re.findall("<varfield id=\"550\" i1=\" \" i2=\" \">(.*?)</varfield>", xml, re.S):
                term = re.search("<subfield label=\"a\">(.*?)</subfield>", rel).group(1)
                related.append(term)

            altLabelEN = []
            altLabelCS = []
            for alt in re.findall("<varfield id=\"450\" i1=\" \" i2=\" \">(.*?)</varfield>", xml, re.S):
                term = re.search("<subfield label=\"a\">(.*?)</subfield>", alt).group(1)
                if ">cze<" in alt: 
                    altLabelCS.append(term)
                else:
                    altLabelEN.append(term)

            heslo = {'id': id,
                     'sysnum': num,
                     'acronym': acronym,
                     'prefLabelCS': prefLabelCS,
                     'prefLabelEN': prefLabelEN,
                     'broader': broader,
                     'related': related,
                     'altLabelCS': altLabelCS,
                     'altLabelEN': altLabelEN,
                     'record_count':get_record_count_for_subject(prefLabelCS)}
            return heslo
        except Exception, e:
            print "".join(["PSH", str(num), " ERROR\n---- STDERR: ", str(e), " ----"])
            return False
    else:
        return False

def get_record_count_for_subject(subject):
    url = 'https://vufind.techlib.cz/vufind/Search/Results?lookfor="%s"&type=psh_facet&submit=Hledat'%subject
    url = re.sub(" ", "+", url)
    
    try:
        catalogue = urllib2.urlopen(url)
        catalogue_html = catalogue.read()
    except Exception, e:
        return 0

    record_count = re.search('class="yui-u first">(.*?)</div>', catalogue_html, re.S)
    if record_count:
        record_count = record_count.group(1)
        record_count = [r for r in re.findall("<b>(.*?)</b>", record_count, re.S)][2].strip(" \n")
        return record_count
    else:
        return 0

def storeSubjectToDB(heslo):
    """Stores subject to database. The parameter heslo is dictionary representation of subject retrieved in function getSubject"""

    hesloCS = Hesla(id_heslo=heslo['id'], heslo=heslo['prefLabelCS'])
    hesloCS.save()

    zkratka = Zkratka(id_heslo=hesloCS, zkratka=heslo['acronym'])
    zkratka.save()

    ekvivalent = Ekvivalence(id_heslo=hesloCS, ekvivalent=heslo['prefLabelEN'])
    ekvivalent.save()

    sysnum = SysNumber(id_heslo=hesloCS, sysnumber=heslo['sysnum'])
    sysnum.save()

    pocet_zaznamu = PocetZaznamu(id_heslo=hesloCS, pocet=heslo['record_count'], pocet_hierarchie=heslo['record_count'])
    pocet_zaznamu.save()

    if heslo['broader']:
        hierarchie = Hierarchie(nadrazeny=heslo['broader'], podrazeny=heslo['id'])
        hierarchie.save()

    for cs in heslo['altLabelCS']:
        variantaCZ = Varianta(varianta=cs, id_heslo=hesloCS, jazyk="cs")
        variantaCZ.save()

    for en in heslo['altLabelEN']:
        variantaEN = Varianta(varianta=en, id_heslo=hesloCS, jazyk="en")
        variantaEN.save()

    for related in heslo['related']:
        pribuzny = Pribuznost(id_heslo=heslo['id'], pribuzny=related)
        pribuzny.save()

    print heslo['prefLabelCS'], heslo['id'], "STORED"

def translateLabel(id):
    """Translates text labels of subjects in database to their PSH id (for tables Hierarchie and Pribuznost)"""
    print "---- Translating labels for current subject----"
    try:
        for subject in Hierarchie.objects.filter(podrazeny=id):
            label = subject.nadrazeny
            subject.nadrazeny = Hesla.objects.raw("".join(["""SELECT * FROM hesla WHERE heslo LIKE '""", label, "'"]))[0].id_heslo
            subject.save()

        for subject in Pribuznost.objects.filter(id_heslo=id):
            label = subject.pribuzny
            subject.pribuzny = Hesla.objects.raw("".join(["""SELECT * FROM hesla WHERE heslo LIKE '""", label, "'"]))[0].id_heslo
            subject.save()
    except Exception:
        print "---- STDERR: Needed subjects are not in the database yet ----"

def translateLabels():
    """Translates text labels of subjects in database to their PSH id (for tables Hierarchie and Pribuznost).
    If error occurs, the program will send an email with PSH subject ID to competent people of PSH department. ;-)"""
    print "---- Translating all labels ----"
    subjectID = ""
    try:
        backup = Hierarchie.objects.exclude(nadrazeny__startswith="PSH")
        for subject in Hierarchie.objects.exclude(nadrazeny__startswith="PSH"):
            label = subject.nadrazeny
            subjectID = subject.podrazeny
            subject.nadrazeny = Hesla.objects.raw("".join(["""SELECT * FROM hesla WHERE heslo LIKE '""", label, "'"]))[0].id_heslo
            subject.save()

        for subject in Pribuznost.objects.exclude(pribuzny__startswith="PSH"):
            label = subject.pribuzny
            subjectID = subject.id_heslo
            subject.pribuzny = Hesla.objects.raw("".join(["""SELECT * FROM hesla WHERE heslo LIKE '""", label, "'"]))[0].id_heslo
            subject.save()

    except Exception, e:
        for heslo in backup:
            deleteSubject(heslo.podrazeny)
        print str(e)
        send_mail(u'Chyba při aktualizaci PSH Manageru', "".join([u'Automatická zpráva o aktualizaci PSH Manageru.\n\nPři aktualizaci PSH Manageru došlo k chybě při vytváření hesla ', subjectID ,u'. Pravděpodobně se jedná o chybu v propojení hesla na neexistující heslo (mylně přečtené/zadané nadřazené nebo příbuzné heslo).\n\nProsím o kontrolu hesla ', subjectID, u'.\n\nDíky, \n\nVáš PSH Manager.']), 'skuta.ctibor@gmail.com', ["kristyna.kozuchova@techlib.cz", "pavlina.omastova@techlib.cz", "eliska.vesela@techlib.cz","skuta.ctibor@gmail.com"], fail_silently=False)
        sys.exit()

def getTopConcepts():
    """Creates table with top concepts of PSH according to their hierarchy."""
    for heslo in Hesla.objects.all():
        try:
            test = Hierarchie.objects.get(podrazeny=heslo.id_heslo)
        except:
            topConcept = Topconcepts(id_heslo=heslo.id_heslo)
            topConcept.save()

def deleteSubject(id):
    """Deletes subject from database according to its PSH id"""
    print "---- Removing:", id, "----"
    try:
        subject = Hesla.objects.get(id_heslo=id)
        subject.delete()

        subjects = Hierarchie.objects.filter(podrazeny=id)
        for obj in subjects:
            obj.delete()

        subjects = Pribuznost.objects.filter(id_heslo=id)
        for obj in subjects:
            obj.delete()

        print id, "REMOVED"

    except Exception, e:
        print "---- STDERR:", str(e), "----"

def getRecordCount():
    """Gets PSH subject records count on server."""
    exp = 10
    previous = 0
    current = 0

    while True:
        previous = current
        current = int(pow(2, exp))
        if not (isValid(current)):
            break
        exp += 1

    minimum = previous
    maximum = current
    mid = int(math.floor((minimum + maximum)/2))

    while (minimum < maximum):
        if minimum + 1 == maximum:
            if isValid(maximum):
                mid = maximum
                break
            else:
                mid = minimum
                break

        if isValid(mid):
            minimum = mid
        else:
            maximum = mid - 1
        mid = int(math.floor((minimum + maximum)/2))

    return mid

def validSubject(xml):
    """Checks if record from server is valid PSH record."""
    if not "<error>" in xml:
        return True
    else:
        return False

def isValid(num):
    """Checks if record from server is valid PSH record according to its number. Used when counting records on server (func getRecordsCount())."""
    test = urllib2.urlopen("http://aleph.techlib.cz/X?op=find_doc&base=STK10&doc_num="+str(num))
    if not "<error>" in test.read():
        return True
    else:
        return False

def get_concept_as_dict(subject_id):
    """Get concept as dict from database according to its PSH ID"""
    heslo = query_to_dicts("""SELECT hesla.id_heslo, 
        hesla.heslo,
        ekvivalence.ekvivalent
        FROM hesla
        LEFT JOIN ekvivalence ON ekvivalence.id_heslo = hesla.id_heslo
        WHERE hesla.id_heslo = '%s'""" %subject_id)

    varianty = query_to_dicts("""SELECT varianta,
        jazyk
        FROM varianta
        WHERE id_heslo = '%s'""" %subject_id)

    podrazeny = query_to_dicts("""SELECT podrazeny
        FROM hierarchie
        WHERE nadrazeny = '%s'""" %subject_id)

    nadrazeny = query_to_dicts("""SELECT nadrazeny
        FROM hierarchie
        WHERE podrazeny = '%s'""" %subject_id)

    pribuzny = query_to_dicts("""SELECT pribuzny
        FROM pribuznost
        WHERE pribuznost.id_heslo = '%s'""" %subject_id)

    zkratka = query_to_dicts("""SELECT zkratka
        FROM psh_zkratka
        WHERE psh_zkratka.id_heslo = '%s'""" %subject_id)

    vazba_wikipedia = query_to_dicts("""SELECT uri_wikipedia
        FROM vazbywikipedia
        WHERE vazbywikipedia.id_heslo = '%s'""" %subject_id)

    hesla = list(heslo)
    if hesla:
        heslo = hesla[0]

        heslo["nadrazeny"] = ""
        for n in nadrazeny:
            heslo["nadrazeny"] = n["nadrazeny"]

        heslo["zkratka"] = list(zkratka)[0]["zkratka"]
        heslo["podrazeny"] = []
        heslo["pribuzny"] = []
        heslo["varianty"] = []

        for p in podrazeny:
            heslo["podrazeny"].append(p["podrazeny"])
        for p in pribuzny:
            heslo["pribuzny"].append(p["pribuzny"])
        for v in varianty:
            heslo["varianty"].append({"varianta": v["varianta"], "jazyk": v["jazyk"]})

        heslo["vazba_wikipedia"] = ""
        for n in vazba_wikipedia:
            print n
            heslo["vazba_wikipedia"] = n["uri_wikipedia"]        
    else:
        heslo = None
    return heslo

def save_update_time():
    update_time = Aktualizace()
    update_time.save()


def get_wikipedia_links():
    subjects = Hesla.objects.all()
    for subject in subjects:
        if not Vazbywikipedia.objects.filter(id_heslo=subject.id_heslo):
            if get_wikipedia_link(subject.heslo):
                print subject.heslo
                link = Vazbywikipedia(id_heslo=subject.id_heslo, uri_wikipedia="".join(["http://cs.wikipedia.org/wiki/", subject.heslo]).encode("utf8"), typ_vazby="exactMatch", overeni=False)
                link.save()


def get_wikipedia_link(subject):
    opener = urllib2.build_opener()
    opener.addheaders = [("User-agent", "Chrome/20.0.1092.0")]
    try:
        wikipedia_page = opener.open("".join(["http://cs.wikipedia.org/wiki/", subject]).encode("utf8"))
        return True
    except urllib2.HTTPError:
        return False

def store_verified_wikipedia_links(filename):
    reader = csv.DictReader(open(filename, "r"))
    i = 0
    for line in reader:
        psh_id = line["Tabulka výsledků"].split("/")[-1]
        if line[""] == "1":
            uri_wikipedia=line["Přiřazený link"]
        else:
            uri_wikipedia=line["Správný link"]
        try:
            link = Vazbywikipedia.objects.get(id_heslo=psh_id)
            link.overeni = True
            link.uri_wikipedia = uri_wikipedia
            link.save()
        except ObjectDoesNotExist:
            link = Vazbywikipedia(id_heslo=psh_id, uri_wikipedia=uri_wikipedia, typ_vazby="exactMatch", overeni=True)
            link.save()

def calculate_hierarchy_record_count():
    hierarchy = Hierarchie.objects.all()
    counts = list(query_to_dicts("""SELECT * FROM psh_pocetzaznamu"""))
    top = Topconcepts.objects.all()
    subject2broader = {}
    subject2count = {}

    for c in counts:
        subject2count[c["id_heslo"]] = c["pocet"]

    for h in hierarchy:
        subject2broader[h.podrazeny] = h.nadrazeny
    
    lowest = set(subject2broader.keys()) - set(subject2broader.values())
    lowest = list(lowest)
    already = set()

    i = 0
    for l in lowest:
        count = subject2count[l]
        lowest_count = count
        current = l
        while current in subject2broader:
            current = subject2broader[current]
            if current in already:
                subject2count[current] += lowest_count
            else:
                subject2count[current] += count
            already.add(current)
            count = subject2count[current]

    for s in subject2count:
        subject = PocetZaznamu.objects.get(id_heslo=s)
        subject.pocet_hierarchie = subject2count[s]
        subject.save()
    return

        


def make_skos():
    header = """<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:dcterms="http://purl.org/dc/terms/"
   xmlns:dctype="http://purl.org/dc/dcmitype/"
   xmlns:foaf="http://xmlns.com/foaf/0.1/"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:skos="http://www.w3.org/2004/02/skos/core#"
   xmlns:xsd="http://www.w3.org/2001/XMLSchema#">
  <skos:ConceptScheme rdf:about="http://psh.ntkcz.cz/skos/">
    <cc:attributionName xml:lang="en">National Technical Library</cc:attributionName>
    <cc:attributionName xml:lang="cs">Národní technická knihovna</cc:attributionName>
    <cc:attributionURL rdf:resource="http://www.techlib.cz/cs/katalogy-a-databaze/psh/"/>
    <cc:legalcode rdf:resource="http://creativecommons.org/licenses/by-nc-sa/3.0/cz/"/>
    <cc:license rdf:resource="http://creativecommons.org/licenses/by-nc-sa/3.0/cz/"/>
    <cc:morePermissions rdf:resource="http://www.techlib.cz/cs/katalogy-a-databaze/psh/"/>
    <dc:creator>
      <rdf:Description>
        <foaf:mbox rdf:resource="mailto:psh@stk.cz"/>
        <foaf:name xml:lang="en">National Technical Library</foaf:name>
        <foaf:name xml:lang="cs">Národní technická knihovna</foaf:name>
      </rdf:Description>
    </dc:creator>
    <dc:description xml:lang="cs">Polytematický strukturovaný heslář je česko-anglický řízený a měnitelný slovník lexikálních jednotek. Slouží k vyjádření věcného obsahu dokumentů a ke zpětnému vyhledání dokumentů na základě věcných kritérií a je určen především pro knihovny s polytematickými fondy.</dc:description>
    <dc:description xml:lang="en">Polythematic Structured Subject Heading System (PSH) is as a tool to organize and search for documents by subject. It is a set of subject headings which can be used to describe the document by subject. In its latest version (2.1) PSH is bilingual (Czech-English). Subject headings in both languages are interconnected. PSH contains over 13 000 subject headings and is divided into 44 thematic sections which have been prepared by experts in the respective disciplines in cooperation with librarians. Each subject heading is included in a hierarchy of six (or - under special circumstances - seven) levels according to its semantic content and specificity. The whole system is a tree structure and it represents various concepts from the most general to the more specific ones.</dc:description>
    <dc:language rdf:resource="http://lexvo.org/id/iso639-3/ces"/>
    <dc:language rdf:resource="http://lexvo.org/id/iso639-3/eng"/>
    <dc:language rdf:datatype="http://purl.org/dc/terms/ISO639-2">cze</dc:language>
    <dc:language rdf:datatype="http://purl.org/dc/terms/ISO639-2">eng</dc:language>
    <dc:publisher>
      <rdf:Description>
        <foaf:mbox rdf:resource="mailto:psh@stk.cz"/>
        <foaf:name xml:lang="en">National Technical Library</foaf:name>
        <foaf:name xml:lang="cs">Národní technická knihovna</foaf:name>
      </rdf:Description>
    </dc:publisher>
    <dc:subject rdf:datatype="http://purl.org/dc/terms/LCC">025.43</dc:subject>
    <dc:subject rdf:datatype="http://purl.org/dc/terms/LCC">Z696.P65</dc:subject>
    <dc:subject xml:lang="cs">předmětová hesla</dc:subject>
    <dc:subject xml:lang="en">subject heading system</dc:subject>
    <dc:subject xml:lang="en">systematic retrieval language</dc:subject>
    <dc:subject xml:lang="cs">systematický selekční jazyk</dc:subject>
    <dc:title xml:lang="cs">Polytematický strukturovaný heslář</dc:title>
    <dc:title xml:lang="en">Polythematic Structured Subject Heading System</dc:title>
    <dc:type rdf:resource="http://purl.org/dc/dcmitype/Dataset"/>
    <dcterms:created rdf:datatype="http://www.w3.org/2001/XMLSchema#year">1993</dcterms:created>
    <dcterms:modified>%s</dcterms:modified>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH1"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH10067"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH10355"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH1038"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH10652"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH11322"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH11453"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH11591"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH116"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH11939"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH12008"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH12156"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH1217"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH12314"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH12577"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH13220"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH1781"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH2086"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH2395"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH2596"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH2910"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH320"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH3768"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH4231"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH4439"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH5042"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH5176"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH5450"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH573"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH6445"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH6548"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH6641"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH6914"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH7093"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH7769"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH7979"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH8126"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH8308"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH8613"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH8808"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH9194"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH9508"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH9759"/>
    <skos:hasTopConcept rdf:resource="http://psh.ntkcz.cz/skos/PSH9899"/>
    <foaf:homepage rdf:resource="http://www.techlib.cz/cs/katalogy-a-databaze/psh/"/>
  </skos:ConceptScheme>\n\n"""% datetime.date.today()

    skos_dir = os.path.join(settings.ROOT, "static/skos")
    skos_file = open("%s/psh-skos.rdf" %skos_dir, "w")
    skos_file.write(header)

    hesla = query_to_dicts("""SELECT id_heslo
        FROM hesla""")
    hesla = list(hesla)
    print len(hesla)
    id_hesel = [heslo["id_heslo"] for heslo in hesla]

    for id_heslo in id_hesel:
        print id_heslo
        heslo = get_concept_as_dict(id_heslo)
        skos_file.write("".join(['<skos:Concept rdf:about="http://psh.ntkcz.cz/skos/', heslo["id_heslo"],'">\n']))
        skos_file.write('<skos:inScheme rdf:resource="http://psh.ntkcz.cz/skos/"/>\n')
        skos_file.write("".join(['<dc:identifier>', heslo["id_heslo"],'</dc:identifier>\n']))
        skos_file.write("".join(['<skos:prefLabel xml:lang="cs">', heslo["heslo"],'</skos:prefLabel>\n']).encode("utf8"))
        skos_file.write("".join(['<skos:prefLabel xml:lang="en">', heslo["ekvivalent"],'</skos:prefLabel>\n']).encode("utf8"))
        for varianta in heslo["varianty"]:
            skos_file.write("".join(['<skos:altLabel xml:lang="', varianta["jazyk"],'">', varianta["varianta"],'</skos:altLabel>\n']).encode("utf8"))

        for podrazeny in heslo["podrazeny"]:
            skos_file.write("".join(['<skos:narrower rdf:resource="http://psh.ntkcz.cz/skos/', podrazeny,'"/>\n']))

        for pribuzny in heslo["pribuzny"]:
            skos_file.write("".join(['<skos:related rdf:resource="http://psh.ntkcz.cz/skos/', pribuzny,'"/>\n']))

        if heslo["nadrazeny"]:
            skos_file.write("".join(['<skos:broader rdf:resource="http://psh.ntkcz.cz/skos/', heslo["nadrazeny"],'"/>\n']))

        if heslo["vazba_wikipedia"]:
            skos_file.write("".join(['<skos:exactMatch rdf:resource="', heslo["vazba_wikipedia"],'" />\n']).encode("utf-8"))
        skos_file.write("</skos:Concept>\n\n")

    skos_file.write("</rdf:RDF>")
    skos_file.close()

    skos_dir = os.path.join(settings.ROOT, "static/skos")
    os.system("zip -j %s/psh-skos.zip %s/psh-skos.rdf" %(skos_dir, skos_dir))

def map_psh_to_dbpedia():
    print "Mapping PSH to DBPedia..."
    hesla = list(query_to_dicts("""SELECT * FROM ekvivalence"""))
    count = len(hesla)
    i = 1

    for heslo in hesla:
        print "%s/%s"%(i, count)
        dbpedia = psh_mapper.map_to_dbpedia(heslo["ekvivalent"])
        if dbpedia:
            vazba, create = Vazbydbpedia.objects.get_or_create(id_heslo=heslo["id_heslo"], heslo_dbpedia=heslo["ekvivalent"].capitalize(), uri_dbpedia=dbpedia, typ_vazby="exactMatch")
            if create:
                vazba.save()
            print dbpedia
        i += 1



def update():
    """Inititates update of PSH database."""
    save_update_time()
    if len(sys.argv) > 1:
        param = sys.argv[1]
        if param == "-n":
            updatePSH(False)
        elif param == "-a":
            updatePSH(True)
        # elif param == "-w":
        #     get_wikipedia_links()
        elif param == "-dbpedia":
            map_psh_to_dbpedia()
    else:
        updatePSH(False)
    

if __name__ == "__main__":
    # calculate_hierarchy_record_count()
    update()
    #store_verified_wikipedia_links("static/wikipedia_links_verified/1.csv")
    #get_wikipedia_links()
    #createTree()
    #make_skos()
    #subject = getSubject("12206")
    #if subject:
            #deleteSubject(subject["id"])
            #storeSubjectToDB(subject)
            #translateLabel(subject["id"])
