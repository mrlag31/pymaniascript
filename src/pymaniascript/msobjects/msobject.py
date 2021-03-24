class MSObject:
    
    def __init__ (self, name):
        self.name = name
    
    def __str__ (self):
        return f'{self.__class__.__name__}: {self.name}'
    
    def __repr__ (self):
        return f'{self.__class__.__name__}({repr(self.name)})'

# ---

class MSFunction (MSObject):
    
    def __init__(self, name, signatures):
        super().__init__(name)
        self.signatures =signatures

    def valid_signature (self, types):
        signatures = [signature for signature in self.signatures
                      if len(signature) == len(types) + 1]
                
        for i in range(len(types)):
            type = types[i]
            signatures = [signature for signature in signatures
                          if type.is_type(signature[i])]
                
        if len(signatures) >= 1:
            signatures2 = signatures.copy()
            for i in range(len(types)):
                type = types[i]
                signatures2 = [signature for signature in signatures2
                               if type == signature[i]]
            
            if len(signatures2) == 0:
                return signatures[0][-1]
            else:
                return signatures2[0][-1]
        elif len(signatures) == 1:
            return signatures[0][-1]
        else:
            return None
# ---

class MSType (MSObject):
    
    def __init__ (self, name, attributes=None, methods=None, enums=None, parent=None):
        super().__init__(name)
        self.attributes = attributes or dict()
        self.methods    = methods or dict()
        self.enums      = enums or dict()
        self.parent     = parent
    
    def get_attribute (self, name):
        r = self.attributes.get(name, None)
        if r == None and self.parent != None:
            return self.parent.get_attribute(name)
        else:
            return r
    
    def get_method (self, name):
        r = self.methods.get(name, None)
        if r == None and self.parent != None:
            return self.parent.get_method(name)
        else:
            return r
    
    def get_enum (self, name):
        return self.enums.get(name, None)
    
    def is_type (self, other):
        if other == ANY:
            return True
        elif self == other:
            return True
        elif self.parent != None:
            return self.parent.is_type(other)
        else:
            return False
    
    def has_any (self):
        return self == ANY
    
    def has_null (self):
        return False

VOID    = MSType('Void')
INTEGER = MSType('Integer')
REAL    = MSType('Real')
TEXT    = MSType('Text')
BOOLEAN = MSType('Boolean')
IDENT   = MSType('Ident')
INT2    = MSType('Int2')
VEC2    = MSType('Vec2')
INT3    = MSType('Int3')
VEC3    = MSType('Vec3')

ANY     = MSType('Any')
ANY.is_type = lambda x: True

TYPEMAPPING = {
    type.name: type for type in [VOID , INTEGER, REAL, TEXT, BOOLEAN,
                                 IDENT, INT2   , INT3, VEC2, VEC3   ]
}

# ---

class MSValue (MSObject):
    
    def __init__ (self, name, type, const=False, value=None):
        super().__init__(name)
        self.type, self.const = type, const
        self.value = value
    
    def is_type (self, other):
        return self.type.is_type(other)
    
    def get_attribute (self, name):
        return self.type.get_attribute(name)
    
    def get_method (self, name):
        return self.type.get_method(name)

INT2.attributes['X'] = MSValue('X', INTEGER)
INT2.attributes['Y'] = MSValue('Y', INTEGER)

VEC2.attributes['X'] = MSValue('X', REAL)
VEC2.attributes['Y'] = MSValue('Y', REAL)

INT3.attributes['X'] = MSValue('X', INTEGER)
INT3.attributes['Y'] = MSValue('Y', INTEGER)
INT3.attributes['Z'] = MSValue('Z', INTEGER)

VEC3.attributes['X'] = MSValue('X', REAL)
VEC3.attributes['Y'] = MSValue('Y', REAL)
VEC3.attributes['Z'] = MSValue('Z', REAL)

TRUE   = MSValue('True'  , BOOLEAN)
FALSE  = MSValue('False' , BOOLEAN)
NULLID = MSValue('NullId', IDENT)

# ---

class MSArray (MSType):
    
    def __init__ (self, elemtype, keytype):
        super().__init__ (f'{elemtype.name}[{keytype.name if keytype != VOID else ""}]')
        self.attributes['count'] = MSValue('count', INTEGER, True)
        self.elemtype, self.keytype = elemtype, (INTEGER if keytype == VOID else keytype)
        self.associative = 0 if keytype == VOID else 1
        
        if keytype == ANY and elemtype == ANY: self.associative = 2
        
        if self.associative == 0:
            self.methods['sort']          = MSFunction('sort'         , [ (                   self,)    ])
            self.methods['sortreverse']   = MSFunction('sortreverse'  , [ (                   self,)    ])
            self.methods['add']           = MSFunction('add'          , [ (elemtype         , VOID)     ])
            self.methods['addfirst']      = MSFunction('addfirst'     , [ (elemtype         , VOID)     ])
            self.methods['remove']        = MSFunction('remove'       , [ (elemtype         , BOOLEAN)  ])
            self.methods['removekey']     = MSFunction('removekey'    , [ (INTEGER          , BOOLEAN)  ])
            self.methods['exists']        = MSFunction('exists'       , [ (elemtype         , BOOLEAN)  ])
            self.methods['existskey']     = MSFunction('existskey'    , [ (INTEGER          , BOOLEAN)  ])
            self.methods['keyof']         = MSFunction('keyof'        , [ (elemtype         , INTEGER)  ])
            self.methods['clear']         = MSFunction('clear'        , [ (                   VOID,)    ])
            self.methods['containsonly']  = MSFunction('containsonly' , [ (self             , BOOLEAN)  ])
            self.methods['containsoneof'] = MSFunction('containsoneof', [ (self             , BOOLEAN)  ])
            self.methods['slice']         = MSFunction('slice'        , [ (INTEGER          , self),
                                                                          (INTEGER, INTEGER , self)     ])
            self.methods['tojson']        = MSFunction('tojson'       , [ (                  TEXT,)     ])
            self.methods['fromjson']      = MSFunction('fromjson'     , [ (TEXT             , BOOLEAN)  ])
            self.methods['get']           = MSFunction('get'          , [ (INTEGER          , elemtype),
                                                                          (keytype, elemtype, elemtype) ])
        
        elif self.associative == 1:
            array = get_array(elemtype)
            
            self.methods['get']            = MSFunction('get'           , [ (keytype, elemtype),
                                                                            (keytype, elemtype, elemtype) ])
            self.methods['sort']           = MSFunction('sort'          , [ (                   self,)    ])
            self.methods['sortreverse']    = MSFunction('sortreverse'   , [ (                   self,)    ])
            self.methods['sortkey']        = MSFunction('sortkey'       , [ (                   self,)    ])
            self.methods['sortkeyreverse'] = MSFunction('sortkeyreverse', [ (                   self,)    ])
            self.methods['remove']         = MSFunction('remove'        , [ (elemtype         , BOOLEAN)  ])
            self.methods['removekey']      = MSFunction('removekey'     , [ (keytype          , BOOLEAN)  ])
            self.methods['exists']         = MSFunction('exists'        , [ (elemtype         , BOOLEAN)  ])
            self.methods['existskey']      = MSFunction('existskey'     , [ (keytype          , BOOLEAN)  ])
            self.methods['keyof']          = MSFunction('keyof'         , [ (elemtype         , keytype)  ])
            self.methods['clear']          = MSFunction('clear'         , [ (                   VOID,)    ])
            self.methods['containsonly']   = MSFunction('containsonly'  , [ (array            , BOOLEAN)  ])
            self.methods['containsoneof']  = MSFunction('containsoneof' , [ (array            , BOOLEAN)  ])
            self.methods['tojson']         = MSFunction('tojson'        , [ (                   TEXT,)    ])
            self.methods['fromjson']       = MSFunction('fromjson'      , [ (TEXT             , BOOLEAN)  ])
    
    def is_type (self, other):
        r = super().is_type(other)
        if r == False:
            if self.associative == 0:
                return isinstance(other, MSArray) and other.associative != 1 and self.elemtype.is_type(other.elemtype)
            elif self.associative == 1:
                return isinstance(other, MSArray) and other.associative != 0 and self.elemtype.is_type(other.elemtype) and self.keytype.is_type(other.keytype)
            elif self.associative == 2:
                return isinstance(other, MSArray)
        else:
            return r
        
    def has_any(self):
        return self.elemtype.has_any() or self.keytype.has_any()
    
    def has_null(self):
        return self.elemtype.has_null() or self.keytype.has_null()

__ARRAYS = {}
def get_array (elemtype, keytype=VOID):
    key = (elemtype, keytype)
    array = __ARRAYS.get(key, None)
    
    if array == None:
        array = MSArray(elemtype, keytype)
        __ARRAYS[key] = array
    
    return array

# ---

class MSEnum (MSType):
    
    def __init__(self, name, values):
        super().__init__(name)
        self.values = { value: MSValue(value, self, True) for value in values }
    
    def get_value (self, name):
        return self.values.get(name, None)

# ---

class MSClass (MSType):
    
    def __init__ (self, name, parent=None):
        super().__init__(name, parent=parent)
    
    def has_null (self):
        return self == NULL.type

__NULL_CLASS = MSClass('@NULL')
NULL = MSValue('Null', __NULL_CLASS, True)
__NULL_CLASS.is_type = lambda x: isinstance(x, MSClass)

# ---

class MSStruct (MSType):
    
    def __init__(self, name, args):
        super().__init__(name)
        self.attributes = { name: MSValue(name, type) for name, type in args.items() }
        self.methods['tojson']   = MSFunction('tojson'  , [ (      TEXT,)   ])
        self.methods['fromjson'] = MSFunction('fromjson', [ (TEXT, BOOLEAN) ])

# ---

class MSInclude (MSObject):
    
    def __init__ (self, name, filescope):
        super().__init__(name)
        self.filescope = filescope
    
    def get_element (self, name, type):
        return self.filescope.get_element(name, type)

# ---

class MSLabel (MSObject):
    pass