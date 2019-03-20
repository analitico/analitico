# reformat source code using black at 120 chars per line
# https://github.com/ambv/black
cd ~/analitico/source
black *.py */*.py */*/*.py */*/*/*.py -l 120
