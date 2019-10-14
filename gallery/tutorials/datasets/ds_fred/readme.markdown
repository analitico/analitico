---
title: 'Tutorial: Reading data from external sites to Parquet.'
description: 'A tutorial showing how to read data from an external site to a compact Parquet file and chart it daily.'
date: 2019-07-21 10:10:00
tags:
- tutorial
- parquet
position: 100
---

## Getting Setup

Before we get started we need to install a library that will help us read data from the Federal Reserve Economic Data (FRED) site. Since this library is not part of the Anaconda standard distribution that Analitico is based on, we will install it in our Jupyter notebook:

```py
!pip install pandas_datareader
import pandas_datareader as pdr
```

## Reading data 

To begin, we read data from FRED into a standard Pandas DataFrame. We then save the dataframe into a file which becomes part of this recipe.

```py
rates = pdr.get_data_fred('DGS10')
rates.to_parquet("rates.parquet")
```

## Charting

To visualize this data we can use a simple mathplotlib chart like this:

```py
# We setup mathplotlib first...
import matplotlib.pyplot as plt
plt.close('all')

# Then chart our data
rates.plot()
```

Voilà!  

![Chart](assets/chart.png)

