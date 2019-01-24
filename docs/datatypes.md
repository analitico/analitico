
## Analitico

Analitico supports the following data types:  
- string / text can be plain, processed, tokenized, collection of items, etc
- integer / integer numbers (pandas int64)
- double / floating point numbers (pandas float64)
- boolean / true-false (pandas bool)
- datetime / date and time (pandas datetime64) 
- timespan / difference between datetime (pandas timedelta64)
- category / categorical entries (pandas category)

Data is received from a source and converted internally to these data types then can be output as a pandas dataset for further processing.  

##
## Other Platforms
##

### PyTorch

PyTorch data types are basically just int and float 
with various levels of precision and implemented in regular
and GPU format. Everything non numeric is preprocessed to numeric.  

https://pytorch.org/docs/stable/tensors.html

### Tensorflow

Tensorflow supports floating point, integers, unsigned integers, strings, booleans, 
complex numbers and integers with quantized ops. All these basically translate to numpy
types. Tensors are built on top of these basic data types.  

https://pythonprogramminglanguage.com/tensorflow-datatypes/

### BigML

BigML support the following data types:  
- numeric / includes both integer and float  
- categorical / similar to pandas category  
- date-time / similar to pandas datetime64, uses iso8601 for base encoding  
- text / plain strings with support for tokenization  
- items / collection of tags (based on pipe delimited strings for example)
   
https://readthedocs.org/projects/bigml/downloads/pdf/stable/

### Pandas

Pandas supports these types:  
- object / normally a string, used for text (numpy string)  
- int64 / integer numbers  
- float64 / floating point numbers  
- bool / true-false values  
- datetime64 / date and time values  
- timedelta64 / difference between datetimes  
- category / finite list of text values  

http://pbpython.com/pandas_dtypes.html

### Azure Machine Learning Studio

The following data types are recognized by Machine Learning Studio:  
string, integer, double, boolean, datetime, timespan  

https://docs.microsoft.com/en-us/azure/machine-learning/studio/import-data

##
## More
##

Dates format RFC3339/ISO8601  
https://www.ietf.org/rfc/rfc3339.txt  
https://en.wikipedia.org/wiki/ISO_8601  

Processing time and time zones:  
http://pytz.sourceforge.net  

