import analitico
import catboost
import pandas as pd

from sklearn.model_selection import train_test_split
from catboost import CatBoostRegressor, Pool

try:

    api = analitico.authorize("tok_xxx")
    # ds = api.get_dataset("ds_houses")
    ds = api.get_dataset("ds_housesalesprediction")
    df = ds.get_dataframe()

    df = df.drop(["date"], axis=1)

    if False:
        s1 = pd.Series(range(0, 100))
        s2 = pd.Series(range(100, 200))
        s3 = pd.Series(range(200, 300))
        df = pd.DataFrame({"serie1": s1, "serie2": s2, "price": s3})

    data = df.loc[:, df.columns != "price"]
    labels = df.loc[:, df.columns == "price"]

    train_data, test_data, train_labels, test_labels = train_test_split(data, labels, test_size=0.20, random_state=42)

    print("training records: %d" % len(train_data))
    print("test records: %d" % len(test_data))

    train_pool = Pool(train_data, train_labels)
    test_pool = Pool(test_data, test_labels)

    model = catboost.CatBoostRegressor(iterations=100, learning_rate=1, depth=8)
    model.fit(train_pool, eval_set=test_pool)

    print("done")

except Exception as exc:
    print(exc)
