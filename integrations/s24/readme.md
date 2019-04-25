
## AnaliticoSdk

To upload a table asset to analitico, you need to perform a multipart encoded POST request to the URL below. The dataset for each table has already been created on the system. The new asset will be used instead of the previous file.

HTTP POST
`https://staging.analitico.ai/api/datasets/ds_s24_<table>/assets/<table>.csv`

For example:
`https://staging.analitico.ai/api/datasets/ds_s24_courier/assets/courier.csv`

Utility methods for Analitico  
`analitico-sdk/analitico.py`

Example of loading all .csv files into Analitico  
`analitico-sdk/upload-tables.py`

To launch Jupyter and run the notebooks:  
`./jupyter.sh`
