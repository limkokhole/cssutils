"""Testcases for cssutils.css.CSSValue and CSSPrimitiveValue."""
__version__ = '$Id: test_cssvalue.py 1473 2008-09-15 21:15:54Z cthedot $'

# from decimal import Decimal # maybe for later tests?
import xml.dom
import basetest
import cssutils
import types

class XTestCase(basetest.BaseTestCase):

    def setUp(self):
        pass

    def test_prioriy(self):
        "Property.priority"
        s = cssutils.parseString('a { color: red }')
        self.assertEqual(u'a {\n    color: red\n    }', s.cssText)
#        self.assertEqual(u'', s.cssRules[0].style.getPropertyPriority('color'))
#
#        s = cssutils.parseString('a { color: red !important }')
#        self.assertEqual(u'a {\n    color: red !important\n    }', s.cssText)
#        self.assertEqual(u'important', s.cssRules[0].style.getPropertyPriority('color'))
#        
#        cssutils.log.raiseExceptions = True
#        p = cssutils.css.Property(u'color', u'red', u'')
#        self.assertEqual(p.priority, u'')
#        p = cssutils.css.Property(u'color', u'red', u'!important')
#        self.assertEqual(p.priority, u'important')
#        self.assertRaisesMsg(xml.dom.SyntaxErr, 
#                             u'', 
#                             cssutils.css.Property, u'color', u'red', u'x')
#
#        cssutils.log.raiseExceptions = False
#        p = cssutils.css.Property(u'color', u'red', u'!x')
#        self.assertEqual(p.priority, u'x')
#        p = cssutils.css.Property(u'color', u'red', u'!x')
#        self.assertEqual(p.priority, u'x')
#        cssutils.log.raiseExceptions = True
#        
#        
#        # invalid but kept!
##        #cssutils.log.raiseExceptions = False
##        s = cssutils.parseString('a { color: red !x }')
##        self.assertEqual(u'a {\n    color: red !x\n    }', s.cssText)
##        self.assertEqual(u'x', s.cssRules[0].style.getPropertyPriority('color'))
#        

if __name__ == '__main__':
    import unittest
    unittest.main()
