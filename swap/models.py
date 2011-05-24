from django.db import models

# Create your models here.
class Page(models.Model):
    url = models.CharField(max_length=1024)
    original = models.TextField()
    raw = models.TextField()

class CSSAsset(models.Model):
    url = models.CharField(max_length=1024)
    original = models.TextField()
    raw = models.TextField()
    page = models.ForeignKey(Page)
