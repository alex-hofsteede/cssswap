from django.db import models
import uuid

# Create your models here.
class CachedPage(models.Model):
    """ Cache of pages by URL - to stop us from having to re-fetch the same URL again """
    url = models.CharField(max_length=1024)
    original = models.TextField()
    date = models.DateTimeField()

class Page(models.Model):
    @classmethod
    def create(cls):
       return Page(uuid=uuid.uuid4().hex[:8])
        
    uuid = models.CharField(max_length=8)
    name = models.CharField(max_length=256)
    url = models.CharField(max_length=1024)
    original = models.TextField()
    raw = models.TextField()

class CSSAsset(models.Model):
    @classmethod
    def create(cls):
       return CSSAsset(uuid=uuid.uuid4().hex[:8])

    uuid = models.CharField(max_length=8)
    name = models.CharField(max_length=256)
    url = models.CharField(max_length=1024)
    original = models.TextField()
    raw = models.TextField()
    page = models.ForeignKey(Page)
