from .msobject import (MSClass, MSValue, get_array, MSEnum  , MSFunction ,
                       VOID   , INTEGER, REAL     , TEXT    , BOOLEAN    ,
                       IDENT  , INT2   , INT3     , VEC2    , VEC3       ,
                       TRUE   , FALSE  , NULL     , NULLID  , ANY        ,
                       MSType , MSArray, MSInclude, MSStruct, MSLabel)

from .classes import compute_classes, CLASSES
from .namespaces import compute_namespaces, NAMESPACES

compute_classes(); compute_namespaces()
del compute_classes, compute_namespaces

CAST        = MSFunction('cast'       , [                       ])
LOG         = MSFunction('log'        , [ (ANY    , VOID)       ])
WAIT        = MSFunction('wait'       , [ (BOOLEAN, VOID)       ])
SLEEP       = MSFunction('sleep'      , [ (INTEGER, VOID)       ])
ASSERT      = MSFunction('assert'     , [ (BOOLEAN, VOID),
                                          (BOOLEAN, TEXT, VOID) ])
TUNINGSTART = MSFunction('tuningstart', [ (VOID   ,)            ])
TUNINGMARK  = MSFunction('tuningmark' , [ (TEXT   , VOID)       ])
TUNINGEND   = MSFunction('tuningend'  , [ (VOID   ,)            ])
TRANSLATE   = MSFunction('_'          , [ (TEXT   , TEXT)       ])
DUMP        = MSFunction('dump'       , [ (ANY    , TEXT)       ])
DUMPTYPE    = MSFunction('dumptype'   , [                       ])

CAST.valid_signature     = lambda x: (x[0] if len(x) == 2 and isinstance(x[1], MSClass)  else None)
DUMPTYPE.valid_signature = lambda x: (TEXT if len(x) == 1 and isinstance(x[0], MSStruct) else None)