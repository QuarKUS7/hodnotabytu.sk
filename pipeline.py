import os
import time
import logging
import pickle

import hyperopt
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials, space_eval

from sklearn.metrics import mean_absolute_error

import xgboost as xgb
import pandas as pd
import numpy as np

from db.Database import Database
from scraper import init_logger

from sklearn.model_selection import train_test_split

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
        self.best = './model/best'

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

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(X, y, test_size=0.1, random_state=123)

        self.dtrain = xgb.DMatrix(self.X_train, label=self.y_train)

        self.dtest = xgb.DMatrix(self.X_test)

        self.dfull = xgb.DMatrix(X, y)

        self.space = {
            'learning_rate':    hp.choice('learning_rate',    np.arange(0.05, 0.5, 0.05)),
            'max_depth':        hp.choice('max_depth',        np.arange(2, 30, 1, dtype=int)),
            'min_child_weight': hp.choice('min_child_weight', np.arange(1, 8, 1, dtype=int)),
            'colsample_bytree': hp.choice('colsample_bytree', np.arange(0.3, 1, 0.1)),
            'subsample':        hp.uniform('subsample', 0.8, 1),
            'n_estimators':     hp.choice('n_estimators',     np.arange(100, 2000, 100,dtype=int))
        }

    def score(self, params):

        model = xgb.XGBRegressor(**params)

        model.fit(self.X_train, self.y_train, verbose=False)

        Y_pred = model.predict(self.X_test)

        score = mean_absolute_error(self.y_test, Y_pred)

        print(score)

        return {'loss': score, 'status': STATUS_OK}

    def optimize(self, trials, space):

        best = fmin(self.score, space, algo=tpe.suggest, max_evals=100)
        return best

    def find_best_model(self):

        trials = Trials()

        best_params = self.optimize(trials, self.space)

        self.best_params = space_eval(self.space, best_params)

        print(self.best_params)

    def train_model(self):

        self.xg_reg = xgb.train(self.best_params, self.dtrain, num_boost_round=250)

        print(sorted( ((v,k) for k,v in self.xg_reg.get_score(importance_type='weight').items()), reverse=True))

        # Predict on testing and training set
        y_pred = self.xg_reg.predict(self.dtest)

        # Report testing and training RMSE
        self.mae = mean_absolute_error(self.y_test, y_pred)

        print(self.mae)

        self.xg_reg = xgb.train(self.best_params, self.dfull, num_boost_round=250)


    def save_model(self):

        best_model = os.path.basename(os.path.realpath(self.best))
        score = int(float(best_model.split('_')[-1]))

        if score <= self.mae:
            log.info('New score {} is higher than present lowest {} score!'.format(score, self.mae))
            return

        model_name = 'model_{}'.format(str(self.mae))

        pickle.dump(self.xg_reg, open('model/{}'.format(model_name), 'wb'))

        try:
            os.unlink(self.best)

        except FileNotFoundError:
            log.warning('No best soft link was found!')

        os.symlink(model_name, './model/best')

    def run_pipeline(self):

        self.log.info('Pipeline started!')

        self.get_data()

        self.clean_data()

        self.make_dummies_from_cat()

        self.make_data_matrix()

        self.find_best_model()

        self.train_model()

        self.save_model()

        self.log.info('Pipeline finished!')


if __name__ == '__main__':

    log = init_logger()

    pipe_db = PipelineDB(log)

    pipe = Pipeline(pipe_db, log)
    pipe.run_pipeline()
