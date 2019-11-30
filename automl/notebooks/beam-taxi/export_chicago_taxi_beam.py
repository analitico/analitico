import absl
from tfx.orchestration.beam.beam_dag_runner import BeamDagRunner

#@title Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.colab import drive
drive.mount('/content/drive')



import os
import pprint
import tempfile
import urllib

import tensorflow as tf
tf.get_logger().propagate = False
pp = pprint.PrettyPrinter()

import tfx
from tfx.components.evaluator.component import Evaluator
from tfx.components.example_gen.csv_example_gen.component import CsvExampleGen
from tfx.components.example_validator.component import ExampleValidator
from tfx.components.model_validator.component import ModelValidator
from tfx.components.pusher.component import Pusher
from tfx.components.schema_gen.component import SchemaGen
from tfx.components.statistics_gen.component import StatisticsGen
from tfx.components.trainer.component import Trainer
from tfx.components.transform.component import Transform
from tfx.orchestration import metadata
from tfx.orchestration import pipeline
from tfx.orchestration.experimental.interactive.interactive_context import InteractiveContext
from tfx.proto import evaluator_pb2
from tfx.proto import pusher_pb2
from tfx.proto import trainer_pb2
from tfx.proto.evaluator_pb2 import SingleSlicingSpec
from tfx.utils.dsl_utils import csv_input
from tensorflow.core.example import example_pb2


print('TensorFlow version: {}'.format(tf.__version__))
print('TFX version: {}'.format(tfx.__version__))

# This is the root directory for your TFX pip package installation.
_tfx_root = tfx.__path__[0]

# This is the directory containing the TFX Chicago Taxi Pipeline example.
_taxi_root = os.path.join(_tfx_root, 'examples/chicago_taxi_pipeline')

# This is the path where your model will be pushed for serving.
_serving_model_dir = os.path.join(
    tempfile.mkdtemp(), 'serving_model/taxi_simple')

_data_root = tempfile.mkdtemp(prefix='tfx-data')
DATA_PATH = 'https://raw.githubusercontent.com/tensorflow/tfx/master/tfx/examples/chicago_taxi_pipeline/data/simple/data.csv'
_data_filepath = os.path.join(_data_root, "data.csv")
urllib.request.urlretrieve(DATA_PATH, _data_filepath)



# Here, we create an InteractiveContext using default parameters. This will
# use a temporary directory with an ephemeral ML Metadata database instance.
# To use your own pipeline root or database, the optional properties
# `pipeline_root` and `metadata_connection_config` may be passed to
# InteractiveContext. Calls to InteractiveContext are no-ops outside of the
# notebook.
context = InteractiveContext()

example_gen = CsvExampleGen(input=csv_input(_data_root))
context.run(example_gen)

statistics_gen = StatisticsGen(
    examples=example_gen.outputs['examples'])
context.run(statistics_gen)

schema_gen = SchemaGen(
    statistics=statistics_gen.outputs['statistics'],
    infer_feature_shape=False)
context.run(schema_gen)

example_validator = ExampleValidator(
    statistics=statistics_gen.outputs['statistics'],
    schema=schema_gen.outputs['schema'])
context.run(example_validator)

_taxi_constants_module_file = 'taxi_constants.py'

_taxi_transform_module_file = 'taxi_transform.py'

transform = Transform(
    examples=example_gen.outputs['examples'],
    schema=schema_gen.outputs['schema'],
    module_file=os.path.abspath(_taxi_transform_module_file))
context.run(transform)

transform.outputs

train_uri = transform.outputs['transform_output'].get()[0].uri
os.listdir(train_uri)

# Get the URI of the output artifact representing the transformed examples, which is a directory
train_uri = transform.outputs['transformed_examples'].get()[1].uri

# Get the list of files in this directory (all compressed TFRecord files)
tfrecord_filenames = [os.path.join(train_uri, name)
                      for name in os.listdir(train_uri)]

# Create a TFRecordDataset to read these files
dataset = tf.data.TFRecordDataset(tfrecord_filenames, compression_type="GZIP")
decoder = tfdv.TFExampleDecoder()

# Iterate over the first 3 records and decode them using a TFExampleDecoder
for tfrecord in dataset.take(3):
  serialized_example = tfrecord.numpy()
  example = decoder.decode(serialized_example)
  pp.pprint(example)

_taxi_trainer_module_file = 'taxi_trainer.py'

trainer = Trainer(
    module_file=os.path.abspath(_taxi_trainer_module_file),
    transformed_examples=transform.outputs['transformed_examples'],
    schema=schema_gen.outputs['schema'],
    transform_graph=transform.outputs['transform_graph'],
    train_args=trainer_pb2.TrainArgs(num_steps=10000),
    eval_args=trainer_pb2.EvalArgs(num_steps=5000))
context.run(trainer)

# An empty slice spec means the overall slice, that is, the whole dataset.
OVERALL_SLICE_SPEC = evaluator_pb2.SingleSlicingSpec()

# Data can be sliced along a feature column
# In this case, data is sliced along feature column trip_start_hour.
FEATURE_COLUMN_SLICE_SPEC = evaluator_pb2.SingleSlicingSpec(
    column_for_slicing=['trip_start_hour'])

ALL_SPECS = [
    OVERALL_SLICE_SPEC,
    FEATURE_COLUMN_SLICE_SPEC
]

# Use TFMA to compute a evaluation statistics over features of a model.
evaluator = Evaluator(
    examples=example_gen.outputs['examples'],
    model_exports=trainer.outputs['model'],
    feature_slicing_spec=evaluator_pb2.FeatureSlicingSpec(
        specs=ALL_SPECS
    ))
context.run(evaluator)

model_validator = ModelValidator(
    examples=example_gen.outputs['examples'],
    model=trainer.outputs['model'])
context.run(model_validator)

pusher = Pusher(
    model=trainer.outputs['model'],
    model_blessing=model_validator.outputs['blessing'],
    push_destination=pusher_pb2.PushDestination(
        filesystem=pusher_pb2.PushDestination.Filesystem(
            base_directory=_serving_model_dir)))
context.run(pusher)

_runner_type = 'airflow' #@param ["beam", "airflow"]
_pipeline_name = 'chicago_taxi_%s' % _runner_type

# For Colab notebooks only.
# TODO(USER): Fill out the path to this notebook.
_notebook_filepath = (
    '/content/drive/My Drive/automl/taxi_pipeline_interactive.ipynb')

# For Jupyter notebooks only.
# _notebook_filepath = os.path.join(os.getcwd(),
#                                   'taxi_pipeline_interactive.ipynb')

# TODO(USER): Fill out the paths for the exported pipeline.
_tfx_root = os.path.join(os.environ['HOME'], 'tfx')
_taxi_root = os.path.join(os.environ['HOME'], 'taxi')
_serving_model_dir = os.path.join(_taxi_root, 'serving_model')
_data_root = os.path.join(_taxi_root, 'data', 'simple')
_pipeline_root = os.path.join(_tfx_root, 'pipelines', _pipeline_name)
_metadata_path = os.path.join(_tfx_root, 'metadata', _pipeline_name,
                              'metadata.db')

# TODO(USER): Specify components to be included in the exported pipeline.
components = [
    example_gen, statistics_gen, schema_gen, example_validator, transform,
    trainer, evaluator, model_validator, pusher
]

absl.logging.set_verbosity(absl.logging.INFO)

tfx_pipeline = pipeline.Pipeline(
    pipeline_name=_pipeline_name,
    pipeline_root=_pipeline_root,
    components=components,
    enable_cache=True,
    metadata_connection_config=(
        metadata.sqlite_metadata_connection_config(_metadata_path)),

    # direct_num_workers=0 means auto-detect based on the number of CPUs
    # available during  execution time.
    #
    # TODO(b/141578059): The multi-processing API might change.
    beam_pipeline_args = ['--direct_num_workers=0'],

    additional_pipeline_args={})

BeamDagRunner().run(tfx_pipeline)