# Holds information about a classification.
# id can be a string (for human readable convenience
# name is what the user will see on interfgaces
# fill, and border are colors [r,g,b]

class Label(object):
    def __init__(self, id, name, description = None, fill = [255, 255, 255], border = [200, 200, 200], visible = True):
        self.id = id                         #unique, can't change ever. eg. 'porcillopora'
        self.name = name                       #human friendly label for a label eg. Porcillopora Putrescenses
        self.description = None
        self.fill = fill
        self.border = border
        self.visible = True

    def save(self):
        return self.__dict__

