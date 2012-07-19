from django.utils.importlib import import_module

# ------------------------------------------------------------------------
def get_object(path, fail_silently=False):
    # Return early if path isn't a string (might already be an callable or
    # a class or whatever)
    if not isinstance(path, (str, unicode)):
        return path

    dot = path.rindex('.')
    mod, fn = path[:dot], path[dot+1:]

    try:
        return getattr(import_module(mod), fn)
    except (AttributeError, ImportError):
        if not fail_silently:
            raise