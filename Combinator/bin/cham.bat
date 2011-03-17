@echo off
python -c "import os; import sys; from combinator.chameleon import remain; remain(sys.argv[1:])" %0 %*
@echo on
:::: will probably want %~f0 at some point
