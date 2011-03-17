# This file is necessary to make this directory a package

def _removeImport(mod):
    # Prior to 2.4, you could end up with broken crap in sys.modules
    import sys
    if sys.version_info < (2,4):
        if mod in sys.modules:
            del sys.modules[mod]
