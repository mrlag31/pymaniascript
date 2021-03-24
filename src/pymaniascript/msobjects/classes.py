from .msobject import (MSClass   , MSValue    , get_array, MSEnum ,
                       MSFunction, TYPEMAPPING)

from pymaniascript.doch import get_doch, NAMESPACE

CLASSES = dict()

__PREPROCESSED = ['Void', 'Integer', 'Real', 'Boolean', 'Text', 'Vec2', 'Vec3', 'Int2', 'Int3', 'Ident', 'Array', 'AssociativeArray']

def __compute_type (name):
    if   name in TYPEMAPPING:
        return TYPEMAPPING[name]
    
    elif name in CLASSES:
        return CLASSES[name]
    
    elif name.startswith('Array'):
        elemtype = __compute_type(name[6:-2])
        return get_array(elemtype)
    
    elif name.startswith('AssociativeArray'):
        elemtype, keytype = name[17:-2].split(', ')
        elemtype, keytype = __compute_type(elemtype), __compute_type(keytype)
        return get_array(elemtype, keytype)
    
    elif '::' in name:
        class_name, enum_name = name.split('::')
        return CLASSES[class_name].get_enum(enum_name)
    
    else:
        raise Exception(f'Invalid type in doch: {name}')

def compute_classes (filename=None):
    if len(CLASSES) != 0: return
    
    doch = get_doch(filename)
    doch_classes = { class_name: class_data for class_name, class_data in doch.items() if
                     not (class_name in __PREPROCESSED or class_name.startswith(NAMESPACE)) }

    # Preallocate classes
    processed = {class_name: False for class_name in doch_classes}
    
    while False in processed.values():
        for class_name in processed:
            if processed[class_name]: continue
            
            inherits = doch[class_name]['inherits']
            if len(inherits) == 0:
                _class = MSClass(class_name)
                CLASSES[class_name] = _class
            else:
                parent_name = inherits[0]['class']
                if parent_name not in CLASSES: continue
                
                parent = CLASSES[parent_name]
                _class = MSClass(class_name, parent=parent)
                CLASSES[class_name] = _class
            
            processed[class_name] = True
    
    # Compute enums
    for class_name, class_data in doch_classes.items():
        _class = CLASSES[class_name]
        
        for enum_data in class_data['enums']['public']:
            enum = MSEnum(enum_data['name'], [value['name'] for value in enum_data['values']])
            _class.enums[enum.name] = enum

    # Compute attributes
    for class_name, class_data in doch_classes.items():
        _class = CLASSES[class_name]
        
        for attribute in class_data['properties']['public']:
            type = attribute['type']
            name = attribute['name']
            
            if type.startswith('const'): type = type[6:]
            type = __compute_type(type)
            
            computed_attr = MSValue(name, type, attribute['constant']==1)            
            _class.attributes[name] = computed_attr
        
        for method in class_data['methods']['public']:
            name = method['name']
            rtype = __compute_type(method['rtnType'])
            method_obj = _class.get_method(name)
            signature = tuple(__compute_type(arg['type']) for arg in method['parameters'])
            signature = (*signature, rtype)
            
            if method_obj == None:
                method_obj = MSFunction(name, signatures=[ signature ])
                _class.methods[name] = method_obj
            else:
                method_obj.signatures.append( signature )