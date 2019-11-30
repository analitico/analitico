
# Categorical features are assumed to each have a maximum value in the dataset.
MAX_CATEGORICAL_FEATURE_VALUES = [24, 31, 12]

CATEGORICAL_FEATURE_KEYS = [
    'trip_start_hour', 'trip_start_day', 'trip_start_month',
    'pickup_census_tract', 'dropoff_census_tract', 'pickup_community_area',
    'dropoff_community_area'
]

DENSE_FLOAT_FEATURE_KEYS = ['trip_miles', 'fare', 'trip_seconds']

# Number of buckets used by tf.transform for encoding each feature.
FEATURE_BUCKET_COUNT = 10

BUCKET_FEATURE_KEYS = [
    'pickup_latitude', 'pickup_longitude', 'dropoff_latitude',
    'dropoff_longitude'
]

# Number of vocabulary terms used for encoding VOCAB_FEATURES by tf.transform
VOCAB_SIZE = 1000

# Count of out-of-vocab buckets in which unrecognized VOCAB_FEATURES are hashed.
OOV_SIZE = 10

VOCAB_FEATURE_KEYS = [
    'payment_type',
    'company',
]

# Keys
LABEL_KEY = 'tips'
FARE_KEY = 'fare'

def transformed_name(key):
  return key + '_xf'