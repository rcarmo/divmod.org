
"""
Benchmark server-side rendering performance of some lightly nested
LiveElement.
"""

from nevow.athena import LiveElement

from xquotient.benchmarks.benchmark_livefragment import main

if __name__ == '__main__':
    main(LiveElement)
