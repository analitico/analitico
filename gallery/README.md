
## Analitico SDK

This package contains plugins and classes used to access analitico.ai cloud services and machine learning models. The package can be installed in Jupyter notebooks, Colaboratory notebooks or other Python environments. To access assets stored in Analitico you will need an API token.

### Installation

To install in Python:  
`pip install analitico`

To install on Jupyter, Colaboratory, etc:  
`!pip install analitico`

### Usage

```python
import analitico

# authorize calls with developer token
sdk = analitico.authorize_sdk(token="tok_xxx")

# retrieve a dataset object from analitico
dataset = sdk.get_dataset("ds_xxx")

# download a data file from storage into a Pandas dataframe
df = dataset.download(df="customers.csv")
```
