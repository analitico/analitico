# analitico.ai

This project includes analitico's website, APIs and libraries. A number of experiments, data sources, queries, jupyter notebooks are also available. Large data files and models are stored externally.
  
  
Environment
---

Create the virtual environment   
`python3 -m venv ~/envs/analitico`   

Activate the environment   
`source ~/envs/analitico/bin/activate`   

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