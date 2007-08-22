"""CSSValue related classes

- CSSValue implements DOM Level 2 CSS CSSValue
- CSSPrimitiveValue implements DOM Level 2 CSS CSSPrimitiveValue
- CSSValueList implements DOM Level 2 CSS CSSValueList

"""
__all__ = ['CSSValue', 'CSSPrimitiveValue', 'CSSValueList']
__docformat__ = 'restructuredtext'
__author__ = '$LastChangedBy$'
__date__ = '$LastChangedDate$'
__version__ = '$LastChangedRevision$'

import re
import types
import xml.dom
import cssutils
import cssproperties
from cssutils.token import Token

class CSSValue(cssutils.util.Base):
    """
    The CSSValue interface represents a simple or a complex value.
    A CSSValue object only occurs in a context of a CSS property

    Properties
    ==========
    cssText
        A string representation of the current value.
    cssValueType
        A (readonly) code defining the type of the value.

    seq: a list (cssutils)
        All parts of this style declaration including CSSComments
    valid: boolean 
        if the value is valid at all, False for e.g. color: #1

    _value
        value without any comments, used by Property to validate
    """

    CSS_INHERIT = 0
    """
    The value is inherited and the cssText contains "inherit".
    """
    CSS_PRIMITIVE_VALUE = 1
    """
    The value is a primitive value and an instance of the
    CSSPrimitiveValue interface can be obtained by using binding-specific
    casting methods on this instance of the CSSValue interface.
    """
    CSS_VALUE_LIST = 2
    """
    The value is a CSSValue list and an instance of the CSSValueList
    interface can be obtained by using binding-specific casting
    methods on this instance of the CSSValue interface.
    """
    CSS_CUSTOM = 3
    """
    The value is a custom value.
    """
    _typestrings = ['CSS_INHERIT' , 'CSS_PRIMITIVE_VALUE', 'CSS_VALUE_LIST', 
                     'CSS_CUSTOM']

    def __init__(self, cssText=None, readonly=False, _propertyName=None):
        """
        inits a new CSS Value

        cssText
            the parsable cssText of the value
        readonly
            defaults to False
        _propertyName
            used to validate this value in the context of a property
            the name must be normalized: lowercase with no escapes
        """
        super(CSSValue, self).__init__()

        self.seq = []
        self.valid = False
        self._value = u''
        self._linetoken = None # used for line report only

        self._propertyName = _propertyName

        if cssText is not None: # may be 0
            self.cssText = cssText

        self._readonly = readonly

    def _getValue(self):
        v = []
        for x in self.seq:
            if isinstance(x, cssutils.css.CSSComment):
                continue
            elif type(x) in types.StringTypes:
                v.append(x)
            else: # maybe CSSPrimitiveValue
                v.append(x.cssText)
        return u''.join(v).strip()
        
#        return u''.join([x for x in self.seq if not isinstance(
#                               x, cssutils.css.CSSComment)]).strip()

    def _setValue(self, value):
        "overwritten by CSSValueList!"
        self._valueValue = value

    _value = property(_getValue, _setValue,
                doc="Actual cssText value of this CSSValue.")

    def _getCssText(self):
        return cssutils.ser.do_css_CSSvalue(self)

    def _setCssText(self, cssText):
        """
        Format
        ======
        ::

            expr = value
              : term [ operator term ]*
              ;
            term
              : unary_operator?
                [ NUMBER S* | PERCENTAGE S* | LENGTH S* | EMS S* | EXS S* |
                  ANGLE S* | TIME S* | FREQ S* | function ]
              | STRING S* | IDENT S* | URI S* | hexcolor
              ;
            function
              : FUNCTION S* expr ')' S*
              ;
            /*
             * There is a constraint on the color that it must
             * have either 3 or 6 hex-digits (i.e., [0-9a-fA-F])
             * after the "#"; e.g., "#000" is OK, but "#abcd" is not.
             */
            hexcolor
              : HASH S*
              ;

        DOMException on setting

        - SYNTAX_ERR: (self)
          Raised if the specified CSS string value has a syntax error
          (according to the attached property) or is unparsable.
        - TODO: INVALID_MODIFICATION_ERR:
          Raised if the specified CSS string value represents a different
          type of values than the values allowed by the CSS property.
        - NO_MODIFICATION_ALLOWED_ERR: (self)
          Raised if this value is readonly.
        """
        def invalidToken(tokens, x):
            """
            raises SyntaxErr if an INVALID token in tokens
    
            x
                used for error message
    
            returns True if INVALID found, else False
            """
            for t in tokens:
                if t.type == self._ttypes.INVALID:
                    return u'Invalid token found in %s.' % x, t
            return False
        
        self._checkReadonly()
        tokens = self._tokenize(cssText)
        msg = invalidToken(tokens, 'value')
        
        if msg:
            self._log.error(
                u'CSSValue: Unknown value syntax: "%s". (%s)' % (
                    self._valuestr(cssText), msg))
            return

        numvalues = 0
        newseq = []
        i, imax = 0, len(tokens)
        while i < imax:
            t = tokens[i]
            if self._ttypes.S == t.type: # add single space
                if not newseq or newseq[-1] == u' ':
                    pass # not 1st and no 2 spaces after each other
                else:
                    newseq.append(u' ')
            elif self._ttypes.COMMENT == t.type: # just add
                newseq.append(cssutils.css.CSSComment(t))
            elif t.type in (
                self._ttypes.SEMICOLON, self._ttypes.IMPORTANT_SYM) or\
                u':' == t.value:
                self._log.error(u'CSSValue: Syntax error.', t)
                return
            elif t.type == self._ttypes.FUNCTION:
                _functokens, endi = self._tokensupto(
                    tokens, funcendonly=True)
                _func = []
                for _t in _functokens:
                    _func.append(_t.value)
                newseq.append(u''.join(_func))
                i += endi #-1
                numvalues += 1
            else:
                newseq.append(t.value)
                numvalues += 1

            i += 1

        if numvalues:
            if tokens:
                self._linetoken = tokens[0] # used for line report
            self.seq = newseq
            self.valid = False
            # validate if known
            if self._propertyName and\
               self._propertyName in cssproperties.cssvalues:
                if cssproperties.cssvalues[self._propertyName](self._value):
                    self.valid = True
                else:
                    self._log.warn(
                        u'CSSValue: Invalid value for CSS2 property %s: %s' %
                        (self._propertyName, self._value), 
                        self._linetoken, neverraise=True)
            else:
                self._log.info(
                    u'CSSValue: Unable to validate as no property context set or unknown property: "%s"'
                    % self._value, neverraise=True)
            
            if self._value == u'inherit':
                self._cssValueType = CSSValue.CSS_INHERIT
                self.__class__ = CSSValue # reset
            elif numvalues == 1:
                self.__class__ = CSSPrimitiveValue
            elif numvalues > 1 and u' ' in newseq:
                self.__class__ = CSSValueList
                self._init() # inits CSSValueList
            else:
                self._cssValueType = CSSValue.CSS_CUSTOM
                self.__class__ = CSSValue # reset
                    
        else:
            self._log.error(
                u'CSSValue: Unknown syntax or no value: "%s".' % self._valuestr(
                    cssText).strip())

    cssText = property(_getCssText, _setCssText,
        doc="A string representation of the current value.")

    def _getCssValueType(self):
        if hasattr(self, '_cssValueType'):
            return self._cssValueType

    cssValueType = property(_getCssValueType,
        doc="A (readonly) code defining the type of the value as defined above.")
    
    def _getCssValueTypeString(self):
        t = self.cssValueType
        if t is not None: # may be 0!
            return CSSValue._typestrings[t]
        else:
            return None

    cssValueTypeString = property(_getCssValueTypeString,
        doc="cssutils: Name of cssValueType of this CSSValue (readonly).")

    def __repr__(self):
        return "cssutils.css.%s(%r, _propertyName=%r)" % (
                self.__class__.__name__, self.cssText, self._propertyName)

    def __str__(self):
        return "<cssutils.css.%s object cssValueType=%r cssText=%r propname=%r valid=%r at 0x%x>" % (
                self.__class__.__name__, self.cssValueTypeString, 
                self.cssText, self._propertyName, self.valid, id(self))


class CSSPrimitiveValue(CSSValue):
    """
    represents a single CSS Value.  May be used to determine the value of a
    specific style property currently set in a block or to set a specific
    style property explicitly within the block. Might be obtained from the
    getPropertyCSSValue method of CSSStyleDeclaration.

    Conversions are allowed between absolute values (from millimeters to
    centimeters, from degrees to radians, and so on) but not between
    relative values. (For example, a pixel value cannot be converted to a
    centimeter value.) Percentage values can't be converted since they are
    relative to the parent value (or another property value). There is one
    exception for color percentage values: since a color percentage value
    is relative to the range 0-255, a color percentage value can be
    converted to a number; (see also the RGBColor interface).
    """
    # constant: type of this CSSValue class
    cssValueType = CSSValue.CSS_PRIMITIVE_VALUE
    
    # An integer indicating which type of unit applies to the value.
    CSS_UNKNOWN = 0 # only obtainable via cssText
    CSS_NUMBER = 1
    CSS_PERCENTAGE = 2
    CSS_EMS = 3
    CSS_EXS = 4
    CSS_PX = 5
    CSS_CM = 6
    CSS_MM = 7
    CSS_IN = 8
    CSS_PT = 9
    CSS_PC = 10
    CSS_DEG = 11
    CSS_RAD = 12
    CSS_GRAD = 13
    CSS_MS = 14
    CSS_S = 15
    CSS_HZ = 16
    CSS_KHZ = 17
    CSS_DIMENSION = 18
    CSS_STRING = 19
    CSS_URI = 20
    CSS_IDENT = 21
    CSS_ATTR = 22
    CSS_COUNTER = 23
    CSS_RECT = 24
    CSS_RGBCOLOR = 25
    # NOT OFFICIAL:
    CSS_RGBACOLOR = 26

    _floattypes = [CSS_NUMBER, CSS_PERCENTAGE, CSS_EMS, CSS_EXS,
                   CSS_PX, CSS_CM, CSS_MM, CSS_IN, CSS_PT, CSS_PC,
                   CSS_DEG, CSS_RAD, CSS_GRAD, CSS_MS, CSS_S,
                   CSS_HZ, CSS_KHZ, CSS_DIMENSION
                   ]
    _stringtypes = [CSS_ATTR, CSS_IDENT, CSS_STRING, CSS_URI]
    _countertypes = [CSS_COUNTER]
    _recttypes = [CSS_RECT]
    _rbgtypes = [CSS_RGBCOLOR, CSS_RGBACOLOR]

    #(String representation for unit types, token type of unit type, detail)
    # used to detect primitiveType and for __repr__
    _unitinfos = [
        ('CSS_UNKNOWN', None, None),
        ('CSS_NUMBER', Token.NUMBER, None),
        ('CSS_PERCENTAGE', Token.PERCENTAGE, None),
        ('CSS_EMS', Token.DIMENSION, 'em'),
        ('CSS_EXS', Token.DIMENSION, 'ex'),
        ('CSS_PX', Token.DIMENSION, 'px'),
        ('CSS_CM', Token.DIMENSION, 'cm'),
        ('CSS_MM', Token.DIMENSION, 'mm'),
        ('CSS_IN', Token.DIMENSION, 'in'),
        ('CSS_PT', Token.DIMENSION, 'pt'),
        ('CSS_PC', Token.DIMENSION, 'pc'),
        ('CSS_DEG', Token.DIMENSION, 'deg'),
        ('CSS_RAD', Token.DIMENSION, 'rad'),
        ('CSS_GRAD', Token.DIMENSION, 'grad'),
        ('CSS_MS', Token.DIMENSION, 'ms'),
        ('CSS_S', Token.DIMENSION, 's'),
        ('CSS_HZ', Token.DIMENSION, 'hz'),
        ('CSS_KHZ', Token.DIMENSION, 'khz'),
        ('CSS_DIMENSION', Token.DIMENSION, None),
        ('CSS_STRING', Token.STRING, None),
        ('CSS_URI', Token.URI, None),
        ('CSS_IDENT', Token.IDENT, None),
        ('CSS_ATTR', Token.FUNCTION, 'attr('),
        ('CSS_COUNTER', Token.FUNCTION, 'counter('),
        ('CSS_RECT', Token.FUNCTION, 'rect('),
        ('CSS_RGBCOLOR', Token.FUNCTION, 'rgb('),
        ('CSS_RGBACOLOR', Token.FUNCTION, 'rgba('),
        ]

    _reNumDim = re.compile(ur'^(.*?)([a-z]+|%)$', re.I| re.U|re.X)

    def __set_primitiveType(self):
        """
        primitiveType is readonly but is set lazy if accessed 
        no value is given as self._value is used
        """
        primitiveType = self.CSS_UNKNOWN
        tokens = self._tokenize(self._value)
        try:
            t = tokens[0]
        except IndexError:
            self._log.error(u'CSSPrimitiveValue: No value.')

        #if self.valid == False:
        #    primitiveType = CSSPrimitiveValue.CSS_UNKNOWN
        if t.type == Token.HASH:
            # special case, maybe should be converted to rgb in any case?
            primitiveType = CSSPrimitiveValue.CSS_RGBCOLOR
        else:
            for i, (name, tokentype, search) in enumerate(CSSPrimitiveValue._unitinfos):
                if t.type == tokentype:
                    if tokentype == Token.DIMENSION:
                        if not search:
                            primitiveType = i
                            break
                        elif re.match(ur'^[^a-z]*(%s)$' % search, t.value):                       
                            primitiveType = i
                            break
                    elif tokentype == Token.FUNCTION:
                        if not search:
                            primitiveType = i
                            break
                        elif t.value.startswith(search):                        
                            primitiveType = i
                            break
                    else:
                        primitiveType = i
                        break
        self._primitiveType = primitiveType
    
    def _getPrimitiveType(self):
        if not hasattr(self, '_primitivetype'):
            self.__set_primitiveType() 
        return self._primitiveType

    primitiveType = property(_getPrimitiveType,
        doc="READONLY: The type of the value as defined by the constants specified above.")

    def _getPrimitiveTypeString(self):
        return CSSPrimitiveValue._unitinfos[self.primitiveType][0]

    primitiveTypeString = property(_getPrimitiveTypeString,
                                   doc="Name of primitive type of this value.")

    def _getCSSPrimitiveTypeString(self, type):
        "get TypeString by given type which may be unknown, used by setters"
        try: 
            return CSSPrimitiveValue._unitinfos[type][0]
        except (IndexError, TypeError):
            return u'%r (UNKNOWN TYPE)' % type

    # oldtype: newType: converterfunc
    _converter = {
        # cm <-> mm <-> in
        (CSS_CM, CSS_MM): lambda x: x * 10,
        (CSS_CM, CSS_IN): lambda x: x * 0.393700787,
        (CSS_MM, CSS_CM): lambda x: x * 0.1,
        (CSS_MM, CSS_IN): lambda x: x * 0.0393700787,
        (CSS_IN, CSS_CM): lambda x: x * 2.54,
        (CSS_IN, CSS_MM): lambda x: x * 25.4,
        # hz <-> khz
        (CSS_KHZ, CSS_HZ): lambda x: x * 1000,
        (CSS_HZ, CSS_KHZ): lambda x: x * 0.001,
        # s <-> ms
        (CSS_S, CSS_MS): lambda x: x * 1000,
        (CSS_MS, CSS_S): lambda x: x * 0.001
        # TODO: convert deg <-> rad <-> grad
    }        

    def __getValDim(self):
        "splits self._value in numerical and dimension part"
        try:
            val, dim = self._reNumDim.findall(self._value)[0]
        except IndexError:
            val, dim = self._value, None
        try:
            val = float(val)
        except ValueError:
            raise xml.dom.InvalidAccessErr(
                u'CSSPrimitiveValue: No float value %s' 
                % (self._value))

        return val, dim

    def getFloatValue(self, unitType):
        """
        (DOM method) This method is used to get a float value in a
        specified unit. If this CSS value doesn't contain a float value
        or can't be converted into the specified unit, a DOMException
        is raised.

        unitType
            to get the float value. The unit code can only be a float unit type
            (i.e. CSS_NUMBER, CSS_PERCENTAGE, CSS_EMS, CSS_EXS, CSS_PX, CSS_CM,
            CSS_MM, CSS_IN, CSS_PT, CSS_PC, CSS_DEG, CSS_RAD, CSS_GRAD, CSS_MS,
            CSS_S, CSS_HZ, CSS_KHZ, CSS_DIMENSION).
            
        returns not necessarily a float but some cases just an int
        e.g. if the value is ``1px`` it return ``1`` and **not** ``1.0``
        
        conversions might return strange values like 1.000000000001
        """
        if unitType not in self._floattypes:
            raise xml.dom.InvalidAccessErr(
                u'unitType Parameter is not a float type')            
        
        val, dim = self.__getValDim()
        
        if self.primitiveType != unitType: 
            try:
                val = self._converter[self.primitiveType, unitType](val) 
            except KeyError:
                raise xml.dom.InvalidAccessErr(
                u'CSSPrimitiveValue: Cannot coerce primitiveType %s to %s' 
                % (self.primitiveTypeString, 
                   self._getCSSPrimitiveTypeString(unitType)))

        return val 

    def setFloatValue(self, unitType, floatValue):
        """
        (DOM method) A method to set the float value with a specified unit.
        If the property attached with this value can not accept the
        specified unit or the float value, the value will be unchanged and
        a DOMException will be raised.

        unitType
            a unit code as defined above. The unit code can only be a float
            unit type
        floatValue
            the new float value which does not have to be a float value but 
            may simple be an int e.g. if setting:: 
            
                setFloatValue(CSS_PX, 1)

        raises DOMException
            - INVALID_ACCESS_ERR: Raised if the attached property doesn't
                support the float value or the unit type.
            - NO_MODIFICATION_ALLOWED_ERR: Raised if this property is readonly.
        """        
        self._checkReadonly()
        if unitType not in self._floattypes:
            raise xml.dom.InvalidAccessErr(u'value is not a float type')
        
        raise NotImplementedError()
        
#        oldval, dim = self.__getValDim()
#        
#        if self.primitiveType != unittype:
#            try:
#                floatValue = self._converter[
#                                self.primitiveType][unitType](floatValue) 
#            except KeyError:
#                raise xml.dom.InvalidAccessErr(
#                u'CSSPrimitiveValue: Cannot coerce primitiveType %s to %s' 
#                % (self.primitiveTypeString, 
#                   self._getCSSPrimitiveTypeString(unitType)))
#                

        # check if possible depending on dim
        self._value = floatValue

    def getStringValue(self):
        """
        (DOM method) This method is used to get the string value. If the
        CSS value doesn't contain a string value, a DOMException is raised.

        Some properties (like 'font-family' or 'voice-family')
        convert a whitespace separated list of idents to a string.
        
        Only the actual value is returned so e.g. all the following return the 
        actual value ``a``: url(a), attr(a), "a", 'a'
        """
        if self.primitiveType not in self._stringtypes:
            raise xml.dom.InvalidAccessErr(
                u'CSSPrimitiveValue %s is not a string type' 
                % self.primitiveTypeString)

        if CSSPrimitiveValue.CSS_STRING == self.primitiveType:
            return self._value[1:-1]
        elif CSSPrimitiveValue.CSS_URI == self.primitiveType:
            return self._value[4:-1]
        elif CSSPrimitiveValue.CSS_ATTR == self.primitiveType:
            return self._value[5:-1]
        else:
            return self._value

    def setStringValue(self, stringType, stringValue):
        """
        (DOM method) A method to set the string value with the specified
        unit. If the property attached to this value can't accept the
        specified unit or the string value, the value will be unchanged and
        a DOMException will be raised.

        stringType
            a string code as defined above. The string code can only be a
            string unit type (i.e. CSS_STRING, CSS_URI, CSS_IDENT, and
            CSS_ATTR).
        stringValue
            the new string value
            Only the actual value is expected so for (CSS_URI, "a") the 
            new value will be ``url(a)``. For (CSS_STRING, "'a'")
            the new value will be ``"\\'a\\'"`` as the surrounding ``'`` are
            not part of the string value

        raises
            DOMException
            - INVALID_ACCESS_ERR: Raised if the CSS value doesn't contain a
                string value or if the string value can't be converted into
                the specified unit.
            - NO_MODIFICATION_ALLOWED_ERR: Raised if this property is readonly.
        """
        self._checkReadonly()
        # self not stringType
        if self.primitiveType not in self._stringtypes:
            raise xml.dom.InvalidAccessErr(
                u'CSSPrimitiveValue %s is not a string type' 
                % self.primitiveTypeString)
        # given stringType is no StringType
        if stringType not in self._stringtypes:
            raise xml.dom.InvalidAccessErr(
                u'CSSPrimitiveValue: stringType %s is not a string type' 
                % self._getCSSPrimitiveTypeString(stringType))

        if self._primitiveType != stringType:
            raise xml.dom.InvalidAccessErr(
                u'CSSPrimitiveValue: Cannot coerce primitiveType %s to %s' 
                % (self.primitiveTypeString, 
                   self._getCSSPrimitiveTypeString(stringType)))

        if CSSPrimitiveValue.CSS_STRING == self._primitiveType:
            self.cssText = u'"%s"' % stringValue.replace(u'"', ur'\\"')
        elif CSSPrimitiveValue.CSS_URI == self._primitiveType:
            self.cssText = u'url(%s)' % stringValue
        elif CSSPrimitiveValue.CSS_ATTR == self._primitiveType:
            self.cssText = u'attr(%s)' % stringValue
        else:
            self.cssText = stringValue
        self._primitiveType = stringType

    def getCounterValue(self):
        """
        (DOM method) This method is used to get the Counter value. If
        this CSS value doesn't contain a counter value, a DOMException
        is raised. Modification to the corresponding style property
        can be achieved using the Counter interface.
        """
        if not self.CSS_COUNTER == self.primitiveType:
            raise xml.dom.InvalidAccessErr(u'Value is not a counter type')
        # TODO: use Counter class    
        raise NotImplementedError()

    def getRGBColorValue(self):
        """
        (DOM method) This method is used to get the RGB color. If this
        CSS value doesn't contain a RGB color value, a DOMException
        is raised. Modification to the corresponding style property
        can be achieved using the RGBColor interface.
        """
        # TODO: what about coercing #000 to RGBColor?
        if self.primitiveType not in self._rbgtypes:
            raise xml.dom.InvalidAccessErr(u'Value is not a RGB value')
        # TODO: use RGBColor class
        raise NotImplementedError()

    def getRectValue(self):
        """
        (DOM method) This method is used to get the Rect value. If this CSS
        value doesn't contain a rect value, a DOMException is raised.
        Modification to the corresponding style property can be achieved
        using the Rect interface.
        """
        if self.primitiveType not in self._recttypes:
            raise xml.dom.InvalidAccessErr(u'value is not a Rect value')
        # TODO: use Rect class
        raise NotImplementedError()
            
    def __str__(self):
        return "<cssutils.css.%s object primitiveType=%s cssText=%r _propertyName=%r valid=%r at 0x%x>" % (
                self.__class__.__name__, self.primitiveTypeString, 
                self.cssText, self._propertyName, self.valid, id(self))
        

class CSSValueList(CSSValue):
    """
    The CSSValueList interface provides the abstraction of an ordered
    collection of CSS values.

    Some properties allow an empty list into their syntax. In that case,
    these properties take the none identifier. So, an empty list means
    that the property has the value none.

    The items in the CSSValueList are accessible via an integral index,
    starting from 0.
    """
    cssValueType = CSSValue.CSS_VALUE_LIST
    __ws = re.compile(ur'^\s*$')
    
    def __init__(self, cssText=None, readonly=False, _propertyName=None):
        """
        inits a new CSSValueList
        """
        super(CSSValueList, self).__init__(cssText=cssText, 
                                       readonly=readonly,
                                       _propertyName=_propertyName)
        self._init()
    
    def _init(self):
        "called by CSSValue if newly identified as CSSValueList"
        self._items = []
        newseq = []
        for v in self.seq: 
            if type(v) in types.StringTypes and not self.__ws.match(v):
                o = CSSValue(cssText=v, _propertyName=self._propertyName)
                self._items.append(o)
                newseq.append(o)
            else:
                newseq.append(v)
        self.seq = newseq
   
    def _getLength(self):
        return len(self._items)

    length = property(_getLength,
                doc="(DOM attribute) The number of CSSValues in the list.")

    def item(self, index):
        """
        (DOM method) Used to retrieve a CSSValue by ordinal index. The
        order in this collection represents the order of the values in the
        CSS style property. If index is greater than or equal to the number
        of values in the list, this returns None.
        """
        try:
            return self._items[index]
        except IndexError:
            return None

    def __iter__(self):
        "CSSValueList is iterable"
        return CSSValueList.__items(self)
        
    def __items(self):
        "the iterator"
        for i in range (0, self.length):
            yield self.item(i)

    def __str_(self):
        return "<cssutils.css.%s object length=%s at 0x%x>" % (
                self.__class__.__name__, self.length, id(self))
