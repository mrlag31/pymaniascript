from .msobject import (MSValue  , get_array, MSEnum     , MSFunction,
                       MSInclude, MSClass  , TYPEMAPPING)
from .classes  import compute_classes, CLASSES

from pymaniascript.doch  import get_doch, NAMESPACE
from pymaniascript.scope import Scope

NAMESPACES = dict()

def __compute_type (name, obj=None):
    if   name in TYPEMAPPING:
        return TYPEMAPPING[name]
    
    elif name in NAMESPACES:
        return NAMESPACES[name]
    
    elif name in CLASSES:
        return CLASSES[name]
    
    elif name.startswith('Array'):
        elemtype = __compute_type(name[6:-2], obj)
        return get_array(elemtype)
    
    elif name.startswith('AssociativeArray'):
        elemtype, keytype = name[17:-2].split(', ')
        elemtype, keytype = __compute_type(elemtype, obj), __compute_type(keytype, obj)
        return get_array(elemtype, keytype)
    
    elif '::' in name:
        parent_name, enum_name = name.split('::')
        parent = __compute_type(parent_name, obj)
        if   isinstance(parent, MSInclude):
            return parent.get_element(enum_name, MSEnum)
        elif isinstance(parent, MSClass):
            return parent.get_enum(enum_name)
    
    elif obj != None:
        return __compute_type(obj.name + '::' + name)
    
    else:
        raise Exception(f'Invalid type in doch: {name}')

def compute_namespaces (filename=None):
    compute_classes(filename)
    if len(NAMESPACES) != 0: return
    
    doch = get_doch(filename)
    doch_namespaces = { elem_name[len(NAMESPACE):]: elem_data for elem_name, elem_data in doch.items() if elem_name.startswith(NAMESPACE) }
    
    # Preallocate namespaces
    for name in doch_namespaces:
        NAMESPACES[name] = MSInclude(name, Scope())
    
    # Compute enums
    for namespace_name, namespace_data in doch_namespaces.items():
        namespace = NAMESPACES[namespace_name]
        
        for enum_data in namespace_data['enums']['private']:
            enum = MSEnum(enum_data['name'], [value['name'] for value in enum_data['values']])
            namespace.filescope.add_element(enum)
    
    # Compute functions and constants
    for namespace_name, namespace_data in doch_namespaces.items():
        namespace = NAMESPACES[namespace_name]
        
        for property in namespace_data['properties']['private']:
            type = property['type']
            name = property['name']
            
            if type.startswith('const'): type = type[6:]
            type = __compute_type(type, namespace)
            
            computed_prop = MSValue(name, type, property['constant']==1)
            namespace.filescope.add_element(computed_prop)

        for function in namespace_data['methods']['private']:
            name = function['name']
            rtype = __compute_type(function['rtnType'], namespace)
            function_obj = namespace.filescope.get_element(name, MSFunction)
            signature = tuple(__compute_type(arg['type'], namespace) for arg in function['parameters'])
            signature = (*signature, rtype)
            
            if function_obj == None:
                function_obj = MSFunction(name, signatures=[ signature ])
                namespace.filescope.add_element(function_obj)
            else:
                function_obj.signatures.append( signature )