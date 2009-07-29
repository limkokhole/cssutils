"""Testcases for cssutils.css.CSSPageRule"""
__version__ = '$Id$'

import xml.dom
import test_cssrule
import cssutils

class CSSPageRuleTestCase(test_cssrule.CSSRuleTestCase):

    def setUp(self):
        super(CSSPageRuleTestCase, self).setUp()
        self.r = cssutils.css.CSSPageRule()
        self.rRO = cssutils.css.CSSPageRule(readonly=True)
        self.r_type = cssutils.css.CSSPageRule.PAGE_RULE#
        self.r_typeString = 'PAGE_RULE'

    def test_init(self):
        "CSSPageRule.__init__()"
        super(CSSPageRuleTestCase, self).test_init()

        r = cssutils.css.CSSPageRule()
        self.assertEqual(u'', r.selectorText)
        self.assertEqual(cssutils.css.CSSStyleDeclaration, type(r.style))
        self.assertEqual(r, r.style.parentRule)

        # until any properties
        self.assertEqual(u'', r.cssText)

        # only possible to set @... similar name
        self.assertRaises(xml.dom.InvalidModificationErr, self.r._setAtkeyword, 'x')

        def checkrefs(ff):
            self.assertEqual(ff, ff.style.parentRule)
            for p in ff.style:
                self.assertEqual(ff.style, p.parent)
                
        checkrefs(cssutils.css.CSSPageRule(
                    style=cssutils.css.CSSStyleDeclaration('font-family: x')))
        
        r = cssutils.css.CSSPageRule()
        r.cssText = '@page { font-family: x }'
        checkrefs(r)
        
        r = cssutils.css.CSSPageRule()
        r.style.setProperty('font-family', 'y')
        checkrefs(r)

        r = cssutils.css.CSSPageRule()
        r.style['font-family'] = 'z'
        checkrefs(r)

        r = cssutils.css.CSSPageRule()
        r.style.fontFamily = 'a'
        checkrefs(r)

    def test_InvalidModificationErr(self):
        "CSSPageRule.cssText InvalidModificationErr"
        self._test_InvalidModificationErr(u'@page')
        tests = {
            u'@pag {}': xml.dom.InvalidModificationErr,
            }
        self.do_raise_r(tests)

    def test_incomplete(self):
        "CSSPageRule (incomplete)"
        tests = {
            u'@page :left { ':
                u'', # no } and no content
            u'@page :left { color: red':
                u'@page :left {\n    color: red\n    }', # no }
        }
        self.do_equal_p(tests) # parse

    def test_cssText(self):
        "CSSPageRule.cssText"
        EXP = u'@page %s {\n    margin: 0\n    }'
        tests = {
            u'@page {}': u'',
            u'@page:left{}': u'',
            u'@page :right {}': u'',
            u'@page {margin:0;}': u'@page {\n    margin: 0\n    }',

            u'@page name { margin: 0 }': EXP % u'name',
            u'@page name:left { margin: 0 }': EXP % u'name:left',
            u'@page name:right { margin: 0 }': EXP % u'name:right',
            u'@page name:first { margin: 0 }': EXP % u'name:first',
            u'@page :left { margin: 0 }': EXP % u':left',
            u'@page :right { margin: 0 }': EXP % u':right',
            u'@page :first { margin: 0 }': EXP % u':first',
            u'@page :UNKNOWNIDENT { margin: 0 }': EXP % u':UNKNOWNIDENT',

            u'@PAGE:left{margin:0;}': u'@page :left {\n    margin: 0\n    }',
            u'@\\page:left{margin:0;}': u'@page :left {\n    margin: 0\n    }',

            # comments
            u'@page/*1*//*2*/:left/*3*//*4*/{margin:0;}':
                u'@page /*1*/ /*2*/ :left /*3*/ /*4*/ {\n    margin: 0\n    }',
            # WS
            u'@page:left{margin:0;}':
                u'@page :left {\n    margin: 0\n    }',
            u'@page\n\r\f\t :left\n\r\f\t {margin:0;}':
                u'@page :left {\n    margin: 0\n    }',
            }
        self.do_equal_r(tests)
        self.do_equal_p(tests)

        tests = {
            u'@page : {}': xml.dom.SyntaxErr,
            u'@page :/*1*/left {}': xml.dom.SyntaxErr,
            u'@page : left {}': xml.dom.SyntaxErr,
            u'@page :left :right {}': xml.dom.SyntaxErr,
            u'@page :left a {}': xml.dom.SyntaxErr,
            # no S between IDENT and PSEUDO
            u'@page a :left  {}': xml.dom.SyntaxErr,

            u'@page :left;': xml.dom.SyntaxErr,
            u'@page :left }': xml.dom.SyntaxErr,
            }
        self.do_raise_p(tests) # parse
        tests.update({
            # false selector
            u'@page :right :left {}': xml.dom.SyntaxErr, # no }
            u'@page :right X {}': xml.dom.SyntaxErr, # no }
            u'@page X Y {}': xml.dom.SyntaxErr, # no }
            
            u'@page :left {': xml.dom.SyntaxErr, # no }
            # trailing
            u'@page :left {}1': xml.dom.SyntaxErr, # no }
            u'@page :left {}/**/': xml.dom.SyntaxErr, # no }
            u'@page :left {} ': xml.dom.SyntaxErr, # no }
            })
        self.do_raise_r(tests) # set cssText

    def test_selectorText(self):
        "CSSPageRule.selectorText"
        r = cssutils.css.CSSPageRule()
        r.selectorText = u'a:left'
        self.assertEqual(r.selectorText, u'a:left')
        
        tests = {
            u'': u'',
            u'name': None,
            u':left': None,
            u':right': None,
            u':first': None,
            u':UNKNOWNIDENT': None,
            u'name:left': None,
            u' :left': u':left',
            u':left': u':left',
            u'/*1*/:left/*a*/': u'/*1*/ :left /*a*/',
            u'/*1*/ :left /*a*/ /*b*/': None,
            u':left/*a*/': u':left /*a*/',
            u'/*1*/:left': u'/*1*/ :left',
            }
        self.do_equal_r(tests, att='selectorText')

        tests = {
            u':': xml.dom.SyntaxErr,
            u':/*1*/left': xml.dom.SyntaxErr,
            u': left': xml.dom.SyntaxErr,
            u':left :right': xml.dom.SyntaxErr,
            u':left a': xml.dom.SyntaxErr,
            u'name :left': xml.dom.SyntaxErr,
            }
        self.do_raise_r(tests, att='_setSelectorText')

    def test_style(self):
        "CSSPageRule.style"
        d = cssutils.css.CSSStyleDeclaration()
        self.r.style = d
        self.assertEqual(d.cssText, self.r.style.cssText)
        self.assertEqual(None, d.parentRule)

    def test_properties(self):
        "CSSPageRule.style properties"
        r = cssutils.css.CSSPageRule()
        r.style.cssText = '''
        margin-top: 0;
        margin-right: 0;
        margin-bottom: 0;
        margin-left: 0;
        margin: 0;

        page-break-before: auto;
        page-break-after: auto;
        page-break-inside: auto;

        orphans: 3;
        widows: 3;
        '''
        exp = u'''@page {
    margin-top: 0;
    margin-right: 0;
    margin-bottom: 0;
    margin-left: 0;
    margin: 0;
    page-break-before: auto;
    page-break-after: auto;
    page-break-inside: auto;
    orphans: 3;
    widows: 3
    }'''
        self.assertEqual(exp, r.cssText)

    def test_reprANDstr(self):
        "CSSPageRule.__repr__(), .__str__()"
        sel=u':left'
        
        s = cssutils.css.CSSPageRule(selectorText=sel)
        
        self.assert_(sel in str(s))

        s2 = eval(repr(s))
        self.assert_(isinstance(s2, s.__class__))
        self.assert_(sel == s2.selectorText)


if __name__ == '__main__':
    import unittest
    unittest.main()
