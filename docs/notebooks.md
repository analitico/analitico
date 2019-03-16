
main change:
- notebooks contain plugins instead of plugins containing notebooks...
- 

notebooks:
- first class citizen in the system like dataset, recipe, model
- a recipe can use a notebook to "do things"
- a model can be a notebook + the data it produced
- notebooks can run in different kernels and languages (opens support for R)
- notebooks can be used to create dashboard pages
- notebooks work the same way inside and outside analitico
- a notebook can be developed in jupyter or colab and then imported in analitico

- INPUT: parameters can be added to a cell before execution
- INPUT: attachments can be added, for example the json in a request or an image in a request
- OUTPUT: files/artifacts can be saved or output attached to a cell


v0:
- a notebook is developed in jupyter or colab implementing linear code
- a notebook has for the most part custom code just like normal notebooks
- notebook can be run inside analitico using papermill to create artifacts
- notebook can be run inside analitico using papermill to generate predictions

v1:
- we develop more and more objects that simplify writing ETL and models in notebooks
- analitico could create the notebook on its own google drive and share with user for editing in colab
- notebooks can be edited and run directly in platform
- we develop a library of notebooks for most use cases including documentation in the notebooks themselves

v2:
- we give ways to edit the notebooks with GUI tools
- the flow becomes more and more to configure notebooks
- a wizard can generate notebooks from templates for common uses cases


##
## Libraries:
##

Parameterize, execute, and analyze notebooks  
https://github.com/nteract/papermill
