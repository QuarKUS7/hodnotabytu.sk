import os
import time
import logging
import pickle

import xgboost as xgb
import pandas as pd
from sklearn.model_selection import train_test_split

from db.Database import Database
from scraper import init_logger


class PipelineDB(Database):

    def __init__(self, log):
        super().__init__(log)

    def get_all_inzeraty(self):
        sql = "SELECT * FROM inzeraty"
        df = pd.read_sql(sql, con=self.cnx)
        return df


class Pipeline():

    def __init__(self, db, log):
        self.db = db
        self.log = log
        self.data = None

    def get_data(self):

        self.data = self.db.get_all_inzeraty()

    def clean_data(self):

        # replace missing with NaN
        self.data  = self.data.replace({-1: None})
        self.data  = self.data.replace({'': None})

        self.data = self.data.drop(['id', 'zdroj', 'timestamp'], axis=1)

        # prilis malo nenulovych hodnot
        self.data = self.data.drop(['balkon', 'lodzia', 'verejne_parkovanie','garaz', 'garazove_statie'], axis=1)

        # model zatial iba pre bratislavu
        self.data = self.data.drop(['okres'], axis=1)

        # ulicu zatial neviem vyuzit
        self.data = self.data.drop(['ulica'], axis=1)

        # cena za m2 nie vhoda feature, kedze ju neni mozne vypocitat z pozorovani
        self.data = self.data.drop(['cena_m2'], axis=1)

        # drop riadkov kde cena je neznama/dohodu
        self.data = self.data[self.data['cena'].notna()]

    def make_dummies_from_cat(self):

        cat_columns = ['mesto','druh','stav', 'kurenie','energ_cert', 'vytah']

        self.data = pd.get_dummies(self.data, columns=cat_columns, prefix=cat_columns)

        self.data.columns = self.data.columns.str.strip()

    def make_data_matrix(self):
        y = self.data['cena']

        X = self.data.drop(['cena'], axis=1)

        self.data_dmatrix = xgb.DMatrix(data=X,label=y)

    def train_model(self):
        params = {"objective":"reg:linear",'colsample_bytree': 0.3,'learning_rate': 0.1,
                'max_depth': 7, 'alpha': 10}

        cv_results = xgb.cv(dtrain=self.data_dmatrix, params=params, nfold=3,
                    num_boost_round=50,early_stopping_rounds=10,metrics="rmse", as_pandas=True, seed=123)

        cv_results.head()

        print((cv_results["test-rmse-mean"]).tail(1))

        self.xg_reg = xgb.train(params=params, dtrain=self.data_dmatrix, num_boost_round=10)

    def save_model(self):

        model_name = 'model_{}'.format(str(time.time()))

        pickle.dump(self.xg_reg, open('model/{}'.format(model_name), 'wb'))

        try:
            os.unlink('./model/best')
        except FileNotFoundError:
            log.warning('No best soft link was found!')

        os.symlink(model_name, './model/best')

    def run_pipeline(self):

        self.log.info('Pipeline started!')

        self.get_data()

        self.clean_data()

        self.make_dummies_from_cat()

        self.make_data_matrix()

        self.train_model()

        self.save_model()

        self.log.info('Pipeline finished!')


if __name__ == '__main__':

    log = init_logger()

    pipe_db = PipelineDB(log)

    pipe = Pipeline(pipe_db, log)
    pipe.run_pipeline()
