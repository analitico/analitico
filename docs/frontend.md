
Angular

##
## Development
##

Prerequisites:  
`sudo apt install npm`  
`sudo npm install -g npm`  
`sudo npm install -g @angular/cli`  

Setup python virtual environment:  
`cd ~/github/analitico`  
`python3 -m venv venv`  
`source venv/bin/activate`  
`pip install -r requirements.txt`  

Run Django server (or launch Django with Visual Studio Code):  
`cd ~/github/analitico/source/`  
`./manage.py runserver`  

Run Angular client:
`cd ~/github/analitico/app/`  
`ng build --prod --watch --output-hashing none`  

##
## Articles
##

Articles on Angular + Django:
https://www.techiediaries.com/django-angular-tutorial/  
https://medium.com/swlh/django-angular-4-a-powerful-web-application-60b6fb39ef34  

