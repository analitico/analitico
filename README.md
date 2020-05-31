# analitico.ai
 
This project includes analitico's website, APIs and libraries. A number of experiments, data sources, queries, jupyter notebooks are also available. Large data files and models are stored externally. 
  
 <a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a> [![CodeFactor](https://www.codefactor.io/repository/github/analitico/analitico/badge?s=a5958aced86f3af20cf6a88be39e3895fd9e34f2)](https://www.codefactor.io/repository/github/analitico/analitico)
 
Environment
---

Install runtime secrets: 
`source ../analitico-ci/analitico-env.sh`


Create the virtual environment   
`python3 -m venv venv`   

Activate the environment   
`source venv/bin/activate`   

Deactivate the environment  
`deactivate`   

See which packages are in use in the environment  
`pip freeze`  

Update requirements file  
`pip freeze > requirements.txt`

Install requirements   
`pip install -r requirements.txt`

Run development server   
`python3 source/manage.py runserver 0.0.0.0:8000`

Run tests  
`cd source`  
`python3 manage.py test`  


Resources
---  

Django Tutorial  
https://docs.djangoproject.com/en/2.1/intro/tutorial01/   

Use Django in Visual Studio Code  
https://code.visualstudio.com/docs/python/tutorial-django  

Django REST Framework   
https://www.django-rest-framework.org/  

GitLab CI/CD Pipelines    
https://gitlab.com/gionata/analitico-api/pipelines

Google Cloud Functions Console   
https://console.cloud.google.com/functions/list?project=analitico-api

How to organize project:   
https://docs.python-guide.org/writing/structure/


Testing
---  

Django Testing Tools     
https://docs.djangoproject.com/en/2.1/topics/testing/tools/  

Visual Studio Code Unit Testing    
https://code.visualstudio.com/docs/python/unit-testing
