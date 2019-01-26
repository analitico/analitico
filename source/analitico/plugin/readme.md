# Possible frameworks/utilities
# https://github.com/pytest-dev/pluggy/
# http://yapsy.sourceforge.net/


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
