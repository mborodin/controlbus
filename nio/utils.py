def get_subclasses(cls):
    subclasses = cls.__subclasses__()
    if len(subclasses) == 0:
        return None
    for subclass in list(subclasses):
        subsubclasses = get_subclasses(subclass)
        if subsubclasses is not None:
            subclasses = subclasses + subsubclasses
    return subclasses
