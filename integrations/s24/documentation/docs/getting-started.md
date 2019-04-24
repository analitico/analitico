# Getting started

## Installation

If you plan on running the provided Python code examples or Jupyter notebooks you will need to create a Python virtual environment first.

```bash
cd 
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```



Before installing [MkDocs][1], you need to make sure you have Python and `pip`
– the Python package manager – up and running. You can verify if you're already
good to go with the following commands:

``` sh
python --version
# Python 2.7.13
pip --version
# pip 9.0.1
```


## Tokens

All calls to Analitico APIs are made using an application token, for example:  
`tok_s24_579E5hOWw7k8`

The application token can be passed using an HTTP header:  
`Authentication: Bearer tok_s24_579E5hOWw7k8`

The application token can also be passed as an HTTP parameter, eg:  
`http://s24.analitico.ai/api/datasets?token=tok_s24_579E5hOWw7k8`

More tokens can be created inside Analitico's backoffice and used to distinguish traffic from different apps, users, etc. if needed.
