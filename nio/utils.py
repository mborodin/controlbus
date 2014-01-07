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