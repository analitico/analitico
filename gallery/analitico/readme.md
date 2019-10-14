### Analitico Package

The library contains code that can be used in Jupyter to complement the analitico.ai online service. For example, the IT manager in your organization could setup an extraction, transformation and loading pipeline (ETL) in analitico and you could then have the data scientist access the resulting data in Jupyter to build his models.  

The architecture is built around plugins. A plugin could, for example, fetch data from source like a CSV file, a SQL database or an Hadoop dataset. A plugin can be used to create a regression model or a neural network for image classification. A plugin can be used to serve inferences from a trained model using a serve on premis, a Kubernetes cluster or a serverless endpoint.

General concepts:
- plugins can contain code that we write
- plugins will contain code from 3rd parties that runs in process (after checks)
- plugins will contain untrusted code (needs to be isolated)
- plugins may have specific requirements.txt for their dependencies
- execution has the concept of environment, variables, etc
- execution has the concept of stages: preflight/sampling, training, testing, inference

Basic plugin class
- input parameters metadata
- output parameters metadata
- id, type, category, description, etc...
- configurations and settings
- process input -> output (one shot or stream)

Dataset plugin
- inputs is a single dataset (or source)
- output is a single dataset

Dataset pipeline (maybe is a plugin itself that aggregates)
- array of plugins and configurations
- process entire pipeline at once

Recipe plugin
- output: a trained model
- output: training statistics (accuracy, etc?)

Trained model
- input: dataset
- output: predictions
