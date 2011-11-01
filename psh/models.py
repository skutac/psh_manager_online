from django.db import models

class Hesla(models.Model):
    id_heslo = models.CharField(max_length=60, primary_key=True)
    heslo = models.CharField(max_length=255, blank=True)
    class Meta:
        db_table = u'hesla'

class SysNumber(models.Model):
    id_heslo = models.ForeignKey('Hesla', db_column="id_heslo", primary_key=True)
    sysnumber = models.IntegerField()

class Ekvivalence(models.Model):
    id_heslo = models.ForeignKey('Hesla', db_column="id_heslo", primary_key=True)
    ekvivalent = models.CharField(max_length=255, blank=True)
    class Meta:
        db_table = u'ekvivalence'

class Hierarchie(models.Model):
    nadrazeny = models.CharField(max_length=60)
    podrazeny = models.CharField(max_length=255, primary_key=True)
    class Meta:
        db_table = u'hierarchie'

class Pribuznost(models.Model):
    id_heslo = models.CharField(max_length=255)
    pribuzny = models.CharField(max_length=255)
    class Meta:
        db_table = u'pribuznost'

class Zkratka(models.Model):
  id_heslo = models.ForeignKey('Hesla', db_column="id_heslo", primary_key=True)
  zkratka = models.CharField(max_length=10)

class Topconcepts(models.Model):
    id_heslo = models.CharField(max_length=36, primary_key=True)
    class Meta:
        db_table = u'topconcepts'

class Varianta(models.Model):
    id_heslo = models.ForeignKey('Hesla', db_column="id_heslo")
    varianta = models.CharField(max_length=255, primary_key=True)
    jazyk = models.CharField(max_length=6)
    class Meta:
        db_table = u'varianta'

class Vazbydbpedia(models.Model):
    id_heslo = models.CharField(max_length=30, primary_key=True)
    heslo_dbpedia = models.CharField(max_length=255)
    uri_dbpedia = models.CharField(max_length=255)
    vazba = models.CharField(max_length=150)
    class Meta:
        db_table = u'vazbydbpedia'

class Vazbylcsh(models.Model):
    id_heslo = models.CharField(max_length=30, primary_key=True)
    heslo_lcsh = models.CharField(max_length=255)
    uri_lcsh = models.CharField(max_length=255)
    vazba = models.CharField(max_length=150)
    class Meta:
        db_table = u'vazbylcsh'

class Vazbyphnk(models.Model):
    id_heslo = models.CharField(max_length=30, primary_key=True)
    sys_phnk = models.IntegerField()
    id_phnk = models.CharField(max_length=36)
    label_phnk = models.CharField(max_length=255)
    typ_vazby = models.CharField(max_length=150)
    class Meta:
        db_table = u'vazbyphnk'
        
class Vazbywikipedia(models.Model):
    id_heslo = models.CharField(max_length=30, primary_key=True)
    heslo_wikipedia = models.CharField(max_length=255)
    uri_wikipedia = models.CharField(max_length=255)
    typ_vazby = models.CharField(max_length=150)
    class Meta:
        db_table = u'vazbywikipedia'

