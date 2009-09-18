class SetWrapper(object):

    def __init__(self, parent, items=()):
        self.items = set()
        self.parent = parent
        self.update(items)

    def add(self, item):
        self.items.add(item)
        self.parent.flat[item] += 1

    def update(self, items):
        for item in set(items).difference(self.items):
            self.parent.flat[item] += 1
        self.items.update(items)

    def discard(self, item):
        if item in self.items:
            self.parent.flat[item] -= 1
        self.items.discard(item)
        if not self.items:
            self.parent.truncate()

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __unicode__(self):
        return repr(list(self.items))

    def __repr__(self):
        return '<SetWrapper(%s)' % unicode(self)

class AutoDiscardDict(object):

    def __init__(self):
        self.items = {}

    def __contains__(self, key):
        return key in self.items

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, key):
        if key not in self.items:
            self.items[key] = 0
        return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value
        if value == 0:
            del self.items[key]

    def __len__(self):
        return len(self.items)

class SetList(object):
    """
    Stores a list of sets with a convenient API.
    """
    def __init__(self, positions=()):
        self.positions = []
        self.flat = AutoDiscardDict()
        self.positions.extend(SetWrapper(self, items) for items in positions)

    def __getitem__(self, index):
        """
        Returns the set at the given index after creating it and
        missing preceding positions if needed.
        """
        while len(self.positions) <= index:
            self.positions.append(SetWrapper(self))
        return self.positions[index]

    def __setitem__(self, index, items):
        """
        Assigns the items into the given index after creating it and
        missing preceding positions if needed.
        """
        position = self[index]
        position.items.clear()
        position.items.update(items)

    def append(self, items):
        self[len(self.positions)].update(items)

    def __len__(self):
        return len(self.positions)

    def __iter__(self):
        return iter(self.positions)

    def truncate(self):
        """
        Truncates empty sets from the end of the positions list
        """
        while self.positions and not self.positions[-1].items:
            self.positions.pop()

    def __unicode__(self):
        return repr([unicode(s) for s in self.positions])

    def __repr__(self):
        return '<SetList %s>' % unicode(self)
