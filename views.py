# -*- coding: utf-8 -*-
import simplejson as json
import re
import csv
from itertools import *

from psh_manager_online import handler
from psh_manager_online.psh.models import Hesla, Varianta, Ekvivalence, Hierarchie, Topconcepts, Pribuznost, Zkratka, Vazbywikipedia, SysNumber, Aktualizace

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

conceptTable = u"""
            <table>
            <tr>
            <td>
            <table>
            <tr>
            <td>
            <div id='titleCS'><span>%s</span><sup id="acronym">%s</sup></div>
            <div id='titleEN'><span>%s</span></div>
            <div id='pshID' data-sysno="%s">%s</div>
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
            <ul class="list" id='related'>%s</ul>
            </td>
            </tr>
            </table>
            </td>
            <td>
            <table>
            <tr>
            <td>
            <div class="title">Nadřazené heslo</div>
            <ul class="list" id="broader">%s</ul>
            </td>
            </tr>
            <tr>
            <td>
            <div class="title">Podřazená hesla</div>
            <ul class="list" id='narrower'>%s</ul>
            </td>
            </tr>
            </table>
            </td>
            </tr>
            </table>
            """

def query_to_dicts(query_string, *query_args):
    """Run a simple query and produce a generator
    that returns the results as a bunch of dictionaries
    with keys for the column values selected.
    """
    cursor = connection.cursor()
    cursor.execute(query_string, query_args)
    col_names = [desc[0] for desc in cursor.description]
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        row_dict = dict(izip(col_names, row))
        yield row_dict
    return

def index(request, subjectID):
   """Returns main site"""
   date_time = Aktualizace.objects.order_by("-datum_cas")[0].datum_cas
   return render_to_response("index.html", {"datetime":date_time})
            
def getSubjectByHash(request, subjectID):
    """Return HTML representation of subject according to given PSH ID"""
    try:
        subject = open("".join([settings.ROOT, "/static/subjects/", subjectID, ".html"]), "r")
        concept = subject.read()
        subject.close()
        return render_to_response("index.html", {'concept': concept})
    except:
        return render_to_response("index.html", {'concept': getConceptFromDB(subjectID)})
    
def suggest(request):
    """Return suggested labels according to given text input and language selector"""
    try:
        if request.POST["en"] == "inactive":
            hesla = Hesla.objects.filter(heslo__istartswith=request.POST["input"])
            alt = Varianta.objects.filter(varianta__istartswith=request.POST["input"], jazyk="cs")
            contains = Hesla.objects.filter(heslo__icontains=request.POST["input"]).exclude(heslo__istartswith=request.POST["input"])
            alt_contains = Varianta.objects.filter(varianta__icontains=request.POST["input"], jazyk="cs").exclude(varianta__istartswith=request.POST["input"], jazyk="cs")
            
            seznam = [heslo.heslo for heslo in hesla]
            
            for heslo in alt:
                seznam.append(heslo.varianta)
            seznam.sort()
            
            seznam_contains = [heslo.heslo for heslo in contains]
            for heslo in alt_contains:
                seznam_contains.append(heslo.varianta)
            seznam_contains.sort()
            seznam.extend(seznam_contains)
            
            return HttpResponse(json.dumps(seznam[0:60]), mimetype='application/json')
        else:
            hesla = Ekvivalence.objects.filter(ekvivalent__istartswith=request.POST["input"])
            alt = Varianta.objects.filter(varianta__istartswith=request.POST["input"], jazyk="en")
            contains = Ekvivalence.objects.filter(ekvivalent__icontains=request.POST["input"]).exclude(ekvivalent__istartswith=request.POST["input"])
            alt_contains = Varianta.objects.filter(varianta__icontains=request.POST["input"], jazyk="en").exclude(varianta__istartswith=request.POST["input"], jazyk="en")
            
            seznam = [heslo.ekvivalent for heslo in hesla]
            
            for heslo in alt:
                seznam.append(heslo.varianta)
            seznam.sort()
            
            seznam_contains = [heslo.ekvivalent for heslo in contains]
            for heslo in alt_contains:
                seznam_contains.append(heslo.varianta)
            seznam_contains.sort()
            seznam.extend(seznam_contains)
            
            return HttpResponse(json.dumps(seznam[0:60]), mimetype='application/json')
            
    except Exception, e:
        return HttpResponse(str(e))

def getSearchResult(request):
    """Return HTML site with search results to given text input and language selector"""
    try:
        substring = request.POST['substring']
        english = request.POST['english']
        result = []
        result.append("".join([u"<h3>Výsledek hledání pro text <i>'", substring, "'</i>:</h3>"]))
        result.append("<ul id='searchResult'>")
        if english == "inactive":
            subjects = Hesla.objects.filter(heslo__istartswith = substring).order_by("heslo")
            result.extend(["".join(["<li itemid='", subject.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.heslo), "</li>"]) for subject in subjects])
            
            subjects = Varianta.objects.filter(varianta__istartswith = substring, jazyk="cs").order_by("varianta")
            result.extend(["".join(["<li itemid='", subject.id_heslo.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.varianta), " (<i>", subject.id_heslo.heslo, "</i>)</li>"]) for subject in subjects])
            
            subjects = Hesla.objects.filter(heslo__contains = substring).order_by("heslo").exclude(heslo__istartswith=substring)
            result.extend(["".join(["<li itemid='", subject.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.heslo), "</li>"]) for subject in subjects])
            
            subjects = Varianta.objects.filter(varianta__contains = substring, jazyk="cs").order_by("varianta").exclude(varianta__istartswith=substring)
            result.extend(["".join(["<li itemid='", subject.id_heslo.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.varianta), " (<i>", subject.id_heslo.heslo, "</i>)</li>"]) for subject in subjects])
            
        else:
            subjects = Ekvivalence.objects.filter(ekvivalent__istartswith = substring).order_by("ekvivalent")
            result.extend(["".join(["<li itemid='", subject.id_heslo.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.ekvivalent), "</li>"]) for subject in subjects])
            
            subjects = Varianta.objects.filter(varianta__istartswith = substring, jazyk="en").order_by("varianta")
            result.extend(["".join(["<li itemid='", subject.id_heslo.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.varianta), " (<i>", Ekvivalence.objects.get(id_heslo=subject.id_heslo.id_heslo).ekvivalent, "</i>)</li>"]) for subject in subjects])
            
            subjects = Ekvivalence.objects.filter(ekvivalent__contains = substring).order_by("ekvivalent").exclude(ekvivalent__istartswith=substring)
            result.extend(["".join(["<li itemid='", subject.id_heslo.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.ekvivalent), "</li>"]) for subject in subjects])
            
            subjects = Varianta.objects.filter(varianta__contains = substring, jazyk="en").order_by("varianta").exclude(varianta__istartswith=substring)
            result.extend(["".join(["<li itemid='", subject.id_heslo.id_heslo ,"' class='clickable heslo'>", bold(substring, subject.varianta), " (<i>", Ekvivalence.objects.get(id_heslo=subject.id_heslo.id_heslo).ekvivalent, "</i>)</li>"]) for subject in subjects])
            
        result.append("</ul>")
    
        return HttpResponse("".join(result))
    except Exception, e:
        return HttpResponse(str(e))
        

def bold(substring, text):
    """Boldify substring within a given text"""
    return re.sub(substring, "".join(["<b>", substring, "</b>"]), text)

def getID(request):
    """Get PSH ID for given text label (translate alternative label to preferred label)"""
    search_term = request.POST["input"]
    
    if request.POST["en"] == 'inactive':
        ids = list(query_to_dicts("""SELECT id_heslo FROM hesla 
                                    WHERE heslo LIKE '%s'"""%"".join(["%%", search_term, "%%"])))
        varianta_ids = list(query_to_dicts("""SELECT id_heslo FROM varianta 
                                    WHERE jazyk = 'cs'
                                    AND varianta LIKE '%s'"""%"".join(["%%", search_term, "%%"])))
    else:
        ids = list(query_to_dicts("""SELECT id_heslo FROM ekvivalence 
                                    WHERE ekvivalent LIKE '%s'"""%"".join(["%%", search_term, "%%"])))
        varianta_ids = list(query_to_dicts("""SELECT id_heslo FROM varianta 
                                    WHERE jazyk = 'en'
                                    AND varianta LIKE '%s'"""%"".join(["%%", search_term, "%%"])))
    ids.extend(varianta_ids)
    if len(ids) != 1:
        subject_id = None
    else:
        subject_id = ids[0]["id_heslo"]

    return HttpResponse(subject_id)

def getConcept(request):
    """Interface for subject retrieval"""
    if request.POST["subjectID"]:
        return HttpResponse(getConceptFromDB(request.POST["subjectID"]))
    else:
        return HttpResponse("POST request did not contain subjectID value")

def getConceptFromDB(subjectID):
        """Get concept form database according to its PSH ID"""
        none = "<li>-</li>"
        try:
            heslo = Hesla.objects.get(id_heslo=subjectID)
            titleCS = heslo.heslo
            acronym = Zkratka.objects.get(id_heslo=subjectID).zkratka
            titleEN = Ekvivalence.objects.get(id_heslo=subjectID).ekvivalent
            sysno = SysNumber.objects.get(id_heslo=subjectID).sysnumber
            
            narrowerID = Hierarchie.objects.filter(nadrazeny=subjectID)
            narrowerObj = [Hesla.objects.get(id_heslo=narrow.podrazeny) for narrow in narrowerID]
            narrowerObj.sort(key=lambda subject: subject.heslo.lower())
            narrower = []
            if len(narrowerObj) > 0:
                for narrow in narrowerObj:
                        narrower.append(u"<li><span itemid='%s' class='clickable heslo'>%s</span>  <sup><a href='/#!%s' class='blank_target' target=blank>>></a></sup></li>"%(narrow.id_heslo, narrow.heslo, narrow.id_heslo))
            else:
                narrower = none
                
            try:
                broader = Hierarchie.objects.get(podrazeny=subjectID)
                broader = u"<li><span itemid='%s' class='clickable heslo'>%s</span>  <sup><a href='/#!%s' class='blank_target' target=blank>>></a></sup></li>"%(broader.nadrazeny ,Hesla.objects.get(id_heslo=broader.nadrazeny).heslo, broader.nadrazeny)
            except:
                broader = none
            
            variantaCS = Varianta.objects.filter(id_heslo=subjectID, jazyk="cs").order_by("varianta")
            nonprefCS = []
            if len(variantaCS) > 0:
                for var in variantaCS:
                    nonprefCS.append("".join(["<li>", var.varianta, "</li>"]))
            else:
                nonprefCS = none
    
            variantaEN = Varianta.objects.filter(id_heslo=subjectID, jazyk="en").order_by("varianta")
            nonprefEN = []
            if len(variantaEN) > 0:
                for var in variantaEN:
                    nonprefEN.append("".join(["<li>", var.varianta, "</li>"]))
            else:
                nonprefEN = none
            
            relatedID = Pribuznost.objects.filter(id_heslo=subjectID)
            relatedObj = [Hesla.objects.get(id_heslo=related.pribuzny) for related in relatedID]
            relatedObj.sort(key=lambda subject: subject.heslo.lower())
            related = []
            if len(relatedObj) > 0:
                for obj in relatedObj:
                    related.append(u"<li><span itemid='%s' class='clickable heslo'>%s</span>  <sup><a href='/#!%s' class='blank_target' target=blank>>></a></sup></li>"%(obj.id_heslo, obj.heslo, obj.id_heslo))
            else:
                related = none
            return conceptTable%(titleCS, acronym, titleEN, sysno, subjectID, "".join(nonprefCS), "".join(nonprefEN), "".join(related), broader, "".join(narrower))
            
        except Exception, e:
            return "".join(["<h3>Heslo s ID <b>'", subjectID, "'</b> neexistuje.</h3>"])
    
def getWikipediaLink(request):
    """Check for wikipedia link"""
    subjectID = request.POST["subjectID"]
    try:
        link = Vazbywikipedia.objects.get(id_heslo=subjectID)
        return HttpResponse(link.uri_wikipedia)
    except Exception, e:
        print str(e)
        return HttpResponse("")

#def saveWikipediaLink(request):
    #"""Save wikipedia link"""
    #subjectID = request.POST["subjectID"]
    #try:
        #heslo = Hesla.objects.get(id_heslo=subjectID)
        #link = Vazbywikipedia(id_heslo=subjectID, uri_wikipedia="".join(["http://cs.wikipedia.org/wiki/", heslo.heslo]), typ_vazby="exactMatch")
        #link.save()
        #return HttpResponse("--- Wikipedia link saved ---")
    #except Exception, e:
        #return HttpResponse(str(e))

def update(request):
    """Update trigger"""
    handler.update()
    return render_to_response('update.html', {})

def get_csv(request):
    hesla = query_to_dicts("""SELECT * FROM hesla""")
    hesla = list(hesla)

    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename="psh.csv"'

    writer = csv.writer(response)
    writer.writerow(['heslo', 'id_heslo'])
    
    for heslo in hesla:
        writer.writerow([heslo["heslo"].encode("utf8"), heslo["id_heslo"]])

    return response