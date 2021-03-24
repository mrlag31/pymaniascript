class Scope:
    
    def __init__ (self, parent=None):
        self.parent = parent
        self.elements = dict()
    
    def get_element (self, name, type, current=False):
        r = self.elements.get(type, None)
        if r != None:
            r = r.get(name, None)
        
        if r == None and self.parent != None and not current:
            return self.parent.get_element(name, type)
        else:
            return r
    
    def add_element (self, obj):
        _type = type(obj)
        if _type not in self.elements:
            self.elements[_type] = dict()
        
        self.elements[_type][obj.name] = obj
    
    def subscope (self):
        return Scope(self)
    
    def topscope (self):
        return self.parent