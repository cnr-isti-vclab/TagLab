# Stores the blobs when user creates, modify or remove blobs in an array of changes (operations)
# Usage is: addBlob when you create a blob, removeBlob when you (guess) remove a blob
# BUT if you want to modify  blob make a copy, remove the original modify the copy and add the copy.
# similar approach when splitting or joining blobs.

class Undo(object):
    def __init__(self):
        self.position = -1
        self.max_undo = 200
        self.operations = []
        self.operation = { 'remove':[], 'add':[], 'class':[], 'newclass':[] }   #current operation

    def addBlob(self, blob):
        self.operation['remove'].append(blob)

    def removeBlob(self, blob):
        self.operation['add'].append(blob)

    def setBlobClass(self, blob, class_name):
        self.operation['class'].append((blob, blob.class_name))
        self.operation['newclass'].append((blob, class_name))

    def saveUndo(self):
        #clip future redo, invalidated by a new change
        self.operations = self.operations[:self.position+1]
        """
        Will mark an undo step using the previously added and removed blobs.
        """
        if len(self.operation['add']) == 0 and len(self.operation['remove']) == 0 and len(self.operation['class']) == 0:
            return

        self.operations.append(self.operation)
        self.operation = { 'remove':[], 'add':[], 'class':[], 'newclass':[] }
        if len(self.operations) > self.max_undo:
            self.operations.pop(0)
        self.position = len(self.operations) -1;

    def undo(self):
        if len(self.operations) is 0:
            return None
        if self.position < 0:
            return None

        # operation = self.undo_operations.pop(-1)
        operation = self.operations[self.position]
        self.position -= 1
        return operation


    def redo(self):
        if self.undo_position >= len(self.operations) - 1:
            return None
        self.undo_position += 1
        operation = self.undo_operations[self.undo_position]
        return operation
