# 101: Hello World tutorial

In this tutorial we'll learn how to train and easily deploy a machine learning model in production with Analitico. The Analitico workflow comes to help and simplify the process where all data scientists get stuck: the deployment.
  
## Analitico Workflow

The road to the deployment is split into three parts:
- Write the model in the Notebook using python & scikit-learn.
- Run the model and create the snapshot.
- Deploy the model to production.


## Write the model

To keep things simple and comprehensive, we will use iris dataset to train a SVM classifier.

```python

# split the data into train and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=10)

# using SVM classifier 
model = SVC(kernel='linear').fit(X_train, y_train)

# calculate test prediction
y_pred = model.predict(X_test)

# save metrics for later training evaluation
analitico.set_model_metrics(y_test, y_pred, model, is_classifier=True)


```

## Run the model and create the snapshot

Now it's time to run the model.  
In the [Notebook](https://analitico.ai/app/recipes/rx_helloworld/notebook) tab, press the `Play` button to execute the notebook on Analitico.

![analitico-run](https://analitico.ai/assets/gallery/run-notebook.png "Analitico Run Notebook")

When the execution completes we are ready to make the Snapshot. The Snapshot contains the model and all the generated artifacts. 
Press the `Actions` button and `Make a Snapshot`. 

![analitico-make-snapshot](https://analitico.ai/assets/gallery/make-snapshot.png "Analitico Make s Snapshot")

## Deploy the model

Ready for the best part. Go to the [Snapshots](https://analitico.ai/app/recipes/rx_helloworld/snapshots) page.  
In this page you see the list of models ready to be deployed.

![analitico-snapshots](https://analitico.ai/assets/gallery/snapshots.png "Analitico Snapshots page")

You can compare the metrics of the models trained over time and choose the best one to candidate for production.
To see the model's generated metrics click the `Actions` button and then `Show Metrics`.

![analitico-show-metrics](https://analitico.ai/assets/gallery/show-metrics.png "Analitico Show Metrics")

![analitico-metrics](https://analitico.ai/assets/gallery/metrics-classification-report.png "Analitico Snapshot's metrics")

Now we are ready to deploy the model into production.  
Press the `Actions` and select `Deploy to Production`.  
Nota: if you prefer to test your model before put it in production, use the `staging` environment instead.  

![analitico-deploy](https://analitico.ai/assets/gallery/deploy.png "Analitico Deployment")


#### That's it!
When the model is deployed you see the `production` label. Click on the label or navigate in the [Live](https://analitico.ai/app/recipes/rx_helloworld/live) tab to retrieve the serverless endpoint url, see the performance charts and the traffic and debug your model through the logs.



