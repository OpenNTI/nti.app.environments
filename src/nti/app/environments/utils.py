
def find_iface(resource, iface):
    while resource is not None:
        if iface.providedBy(resource):
            return resource
        try:
            resource = resource.__parent__
        except AttributeError:
            resource = None
    return None