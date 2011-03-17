@echo off

python -c "from combinator import sysenv; sysenv.export()" > div_env.bat
call div_env.bat

title Divmod Command Shell
cd ..\..\..
cmd
