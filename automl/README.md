


Tensorflow and Tfx require Python 3.6 (not 3.7).
Anaconda and Miniconda start by defaul with Python 3.7
You can downgrade to Python 3.6 with: 
`conda install python=3.6`

Removing all local dockers and cleaning everything:
`docker system purge -a`

Required installations:
`pip install tfx==0.15.0`


This needs to be done BEFORE installing tfx:
conda install psutil