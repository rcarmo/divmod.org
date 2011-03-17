
"""
Benchmark server-side rendering performance of rendering a page with a grabber
scrolltable on it.
"""

from epsilon.scripts.benchmark import start, stop

from axiom.store import Store

from xquotient.grabber import ConfiguredGrabbersView
from xquotient.benchmarks.rendertools import render

N_RENDERS = 500

def main():
    s = Store()
    start()
    for i in xrange(N_RENDERS):
        fragment = ConfiguredGrabbersView(s)
        render(fragment)
    stop()


if __name__ == '__main__':
    main()
