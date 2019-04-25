# Analitico for Supermercato24

This site explains how to access the machine learning services built by Analitico for Supermercato24. We encourage you to edit these documents directly or request more information using the links below.

Help by editing the documentation:  
https://github.com/Supermercato24/analitico-s24/tree/master/notebooks/documentation/docs

Request more documentation by opening an issue here:  
https://github.com/Supermercato24/analitico-s24/issues


## Installation

Prediction services are accessible via HTTP APIs and do not require any special tool to be installed.

Python code samples and Jupyter worksheets on the other hand, require a number of Python libraries to be installed before hand. It's normally easier if you setup a virtual environment that has all the required libraries with the correct versions, etc. 

You can create a virtual environment like this:

``` sh
cd 
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Tokens

Services are deployed over HTTP endpoints requiring proper API tokens for access. This documentation is easy to edit directly in github. If you need a token please write to info@analitico.ai. 

All calls to Analitico APIs are made using an application token, for example:  
`tok_s24_xxyyzz`

The application token can be passed using an HTTP header:  
`Authentication: Bearer tok_s24_xxyyzz`

The application token can also be passed as an HTTP parameter, eg:  
`http://s24.analitico.ai/api/datasets?token=tok_s24_xxyyzz`

More tokens can be created inside Analitico's backoffice and used to distinguish traffic from different apps, users, etc. if needed.

## Contribute

Issue Tracker:   
https://github.com/Supermercato24/analitico-s24/issues

Source Code:   
https://github.com/Supermercato24/analitico-s24

## Support

If you are having issues write to support@analitico.ai or call [+39 392 5353054](tel:+393925353054)

