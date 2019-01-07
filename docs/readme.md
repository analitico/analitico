
Analitico IDE:

Azure Machine Learning Studio but easier.
More wizards to guide people to choosing models.
Streamlined UI with material design
Services deployable using kubernets on provider of choice
Open source
Tutorials in Italian? and other languages?
Support for branded tools like CatBoost and XGBoost
Gallery with examples with european data sources
European Data protection built in from start?


## 
## Azure Machine Learning Studio
##

Workspace
    Container for all things and files
    Manages access rights and user

    Projects
        Used to group other items

    Datasets
        Container for data import and analisys
        Imports from different formats
        Has APIs to update data        

    Experiments
        Implements ML workflow to produce models

    Trained Models
        Saved model usable for inference w/o retraining

    Webservices
        Uses trained models to serve inferences
        Billable

    Notebooks
        Live jupyter notebook with access to datasets
        Could show experiment as source code

    Transforms
        Manipulate datasets

    Modules
        Import custom code from outside platform
        Can also be used to implement internal modules


Ideas:
    - For notebooks could use Colocation with custom SDK keys and code that access platform contents


##
## BigML
##

dashboard

organization
  https://bigml.com/dashboard/organization/acmeinc
  Organizations allow several users to work on the same projects, 
  using the same Dashboard, but at different levels of privileges
