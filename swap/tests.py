"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import unittest
from django.test import TestCase
from swap import util

class CSSUrlTest(TestCase):
    def testmakeCSSURLsAbsolute(self):
        """
        Tests that the CSS URL replacement works for all types of CSS URLs
        """
#Basic @import
        self.assertEquals(util.makeCSSURLsAbsolute('@import url("/my/site.css")',"http://domain.com"),'@import url("http://domain.com/my/site.css")')
#import with no parentheses
        self.assertEquals(util.makeCSSURLsAbsolute('@import url "/my/site.css" ',"http://domain.com"),'@import url "http://domain.com/my/site.css" ')
#import with no 'url'
        self.assertEquals(util.makeCSSURLsAbsolute('@import "/my/site.css" ',"http://domain.com"),'@import "http://domain.com/my/site.css" ')
#import with no 'url' or quotes
        self.assertEquals(util.makeCSSURLsAbsolute('@import /my/site.css ',"http://domain.com"),'@import http://domain.com/my/site.css ')
#non-import
        self.assertEquals(util.makeCSSURLsAbsolute('url("/my/site.css")',"http://domain.com"),'url("http://domain.com/my/site.css")')
#non-import, no quotes
        self.assertEquals(util.makeCSSURLsAbsolute('url(/my/site.css)',"http://domain.com"),'url(http://domain.com/my/site.css)')
#non-import with no parentheses, this is not legal, and should not be matched/changed
        self.assertEquals(util.makeCSSURLsAbsolute('url "/my/site.css"',"http://domain.com"),'url "/my/site.css"')
#non-import with no 'url' or parentheses, this is not legal, and should not be matched/changed
        self.assertEquals(util.makeCSSURLsAbsolute('"/my/site.css"',"http://domain.com"),'"/my/site.css"')

