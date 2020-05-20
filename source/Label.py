# Holds information about a classification.
# id can be a string (for human readable convenience
# name is what the user will see on interfgaces
# fill, and border are colors [r,g,b]

class Label(object):
    def __init__(self):
        self.id = None                         #unique, can't change ever. eg. 'porcillopora'
        self.name = None                       #human friendly label for a label eg. Porcillopora Putrescenses
        self.description = ""
        self.fill = None
        self.border = None

