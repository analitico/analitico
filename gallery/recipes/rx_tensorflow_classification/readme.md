# 101: TensorFlow classification tutorial

In this tutorial we'll learn how to train and easily deploy a machine learning model in production with Analitico. The Analitico workflow comes to help and simplify the process where all data scientists get stuck: the deployment.
  
## Analitico Workflow

The road to the deployment is split into three parts:
- Write the model in the Notebook using python & Tensorflow.Keras.
- Run the model and create the snapshot.
- Deploy the model to production.


## Write the model

To keep things simple and comprehensive, we will use iris dataset to train a simple neural network with TensorFlow.Keras.

```python

# Create a custom model
input_size = X.shape[1]
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(input_size)),
    tf.keras.layers.Dense(8, activation='relu', input_shape=(input_size, )),
    tf.keras.layers.Dense(4, activation='relu', input_shape=(input_size, )),
    tf.keras.layers.Dense(3, activation='softmax', input_shape=(input_size, ))
])

# Compile the model specifying optimizer, metrics and learning rate
model.compile(optimizer="adam",
              loss="sparse_categorical_crossentropy",
              metrics=["accuracy"])    

# Save the model for later predictions from endpoint
checkpoint = tf.keras.callbacks.ModelCheckpoint("iris_classifier_model.hdf5", save_best_only=True)

# Train the model
model.fit(x=X,
          y=y,
          validation_split=0.2,
          batch_size=8,
          epochs=100,
          callbacks=[checkpoint],
          verbose=1)

```

## Run the model and create the snapshot

Now it's time to run the model.  
In the [Notebook](https://analitico.ai/app/recipes/rx_tensorflow_classification/notebook) tab, press the `Play` button to execute the notebook on Analitico.

![analitico-run](https://analitico.ai/assets/gallery/run-notebook.png "Analitico Run Notebook")

When the execution completes we are ready to make the Snapshot. The Snapshot contains the model and all the generated artifacts. 
Press the `Actions` button and `Make a Snapshot`. 

![analitico-make-snapshot](https://analitico.ai/assets/gallery/make-snapshot.png "Analitico Make s Snapshot")

## Deploy the model

Ready for the best part. Go to the [Snapshots](https://analitico.ai/app/recipes/rx_tensorflow_classification/snapshots) page.  
In this page you see the list of models ready to be deployed.

![analitico-snapshots](https://analitico.ai/assets/gallery/snapshots.png "Analitico Snapshots page")

You can compare the metrics of the models trained over time and choose the best one to candidate for production.
To see the model's generated metrics click the `Actions` button and then `Show Metrics`.

![analitico-show-metrics](https://analitico.ai/assets/gallery/show-metrics.png "Analitico Show Metrics")

![analitico-metrics](https://analitico.ai/assets/gallery/metrics.png "Analitico Snapshot's metrics")

Now we are ready to deploy the model into production.  
Press the `Actions` and select `Deploy to Production`.  
Nota: if you prefer to test your model before put it in production, use the `staging` environment instead.  

![analitico-deploy](https://analitico.ai/assets/gallery/deploy.png "Analitico Deployment")


#### That's it!
When the model is deployed you see the `production` label. Click on the label or navigate in the [Live](https://analitico.ai/app/recipes/rx_tensorflow_classification/live) tab to retrieve the serverless endpoint url, see the performance charts and the traffic and debug your model through the logs.






