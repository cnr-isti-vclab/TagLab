class Label(object):
    """
    Label holds information about a classification.
    """

    def __init__(self, id, name, description = None, fill = [255, 255, 255], border = [200, 200, 200], visible = True):

        # id can be a string (for human readable convenience)
        # name is what the user will see on the interface
        # fill, and border are colors [r,g,b]

        self.id = id              # unique, can't change ever. eg. 'pocillopora'
        self.name = name          # human friendly label for a label eg. Pocillopora Putrescenses
        self.description = None
        self.fill = fill
        self.border = border
        self.visible = True

    def getColorAsKey(self):
        """
        It returns the color of the label as a string in the format "rrr-ggg-bbb".
        Example: "200-002-015" for r=200, g=2, b=15
        """

        r = self.fill[0]
        g = self.fill[1]
        b = self.fill[2]

        return "{:03d}-{:03d}-{:03d}".format(r,g,b)

    def save(self):

        return self.__dict__

