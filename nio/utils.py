from queue import Queue

def get_subclasses(cls):
    subclasses = cls.__subclasses__()
    if len(subclasses) == 0:
        return None
    for subclass in list(subclasses):
        subsubclasses = get_subclasses(subclass)
        if subsubclasses is not None:
            subclasses = subclasses + subsubclasses
    return subclasses


def flatten_generator(l):
    """
    List flattening generator
    @param l: Input list
    @type l: list
    @return: Generator
    """
    for i in l:
        if isinstance(i, list) or isinstance(i, tuple):
            for j in flatten(i):
                yield j
        else:
            yield i


def flatten(l):
    """
    Flattening input list i
    @param l: List to be flattened
    @type l: list
    @return: Flat list
    """
    return [i for i in flatten_generator(l)]


class RoundRobin:
    def __init__(self, *iterables):
        self.values = Queue()
        map(self.values.put, flatten(iterables))

    def __iter__(self):
        return self

    def next(self):
        val = self.values.get(0)
        self.values.task_done()
        self.values.put(val)
        return val


class RangeRoundRobin:
    def __init__(self, first, last):
        if first > last:
            raise RuntimeError('Range start is greater than range end')
        self.first = first
        self.last = last
        self.current = first

    def __iter__(self):
        return self

    def next(self):
        val = self.current
        self.current += 1
        if self.current > self.last:
            self.current = self.first
        return val


class LeasedRoundRobin:
    def __init__(self, l):
        self.values = Queue()
        map(self.values.put, l)

    def __iter__(self):
        return self

    def next(self):
        val = self.values.get()
        self.values.task_done()
        return val

    def release(self, val):
        self.values.put(val)
