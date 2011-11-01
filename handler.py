# -*- coding: utf-8 -*-
"""
handler.py [-option]

Handler is module for updating PSH database in PSH Manager project and parts that are dependent on changes made in structure of PSH
(HTML navigation tree, representation of subjects stored in files).

OPTIONS

   -n -downloads only new records from server, cannot take care of changes made in structure of older subjects
   
   -a -iteratively updates each subject in database, it takes a long time but during the process the database is still prepared for use
"""

import os, sys, time, urllib2, math, re, datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_local'

from psh.models import Hesla, Varianta, Ekvivalence, Hierarchie, Topconcepts, Pribuznost, Zkratka, SysNumber

from django.conf import settings
from django.http import HttpResponse
from django.core.mail import send_mail

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
    #count = 15
    print "".join(["Last PSH ID on server: ", str(count)])
    if all == True:
        print "Updating PSH database..."
        last = 0
    else:
        try:
    	   hesla = Hesla.objects.all()
    	   ids = [int(re.sub("PSH", "", heslo.id_heslo)) for heslo in hesla]
    	   last = max(ids)
        except:
	   last = 0
    print "".join(["Last PSH ID in database: ", str(last)])
    
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

        translateLabels()
        createTree() 
    
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
                         'altLabelEN': altLabelEN,}
                return heslo
        except Exception, e:
               print "".join(["PSH", str(num), " ERROR\n---- STDERR: ", str(e), " ----"])
               return None

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
            send_mail(u'Chyba při aktualizaci PSH Manageru', "".join([u'Automatická zpráva o aktualizaci PSH Manageru.\n\nPři aktualizaci PSH Manageru došlo k chybě při vytváření hesla ', subjectID ,u'. Pravděpodobně se jedná o chybu v propojení hesla na neexistující heslo (mylně přečtené/zadané nadřazené nebo příbuzné heslo).\n\nProsím o kontrolu hesla ', subjectID, u'.\n\nDíky, \n\nVáš PSH Manager.']), 'skuta.ctibor@gmail.com', ["kristyna.kozuchova@techlib.cz", "pavlina.omastova@techlib.cz", "skuta.ctibor@gmail.com"], fail_silently=False)
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

def update():
    """Inititates update of PSH database."""
    if len(sys.argv) > 1:
        all = sys.argv[1]
        if all == "-n":
            all = False
        elif all == "-a":
             all = True
        else:
            all = False
    else:
        all = False
    updatePSH(all)
    

if __name__ == "__main__":
    update()
