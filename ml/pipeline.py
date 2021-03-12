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
from logger import init_logger

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
        self.data = self.data.drop(['balkon', 'lodzia', 'verejne_parkovanie', 'orientacia', 'telkoint'], axis=1)

        # model zatial iba pre bratislavu
        self.data = self.data.drop(['okres'], axis=1)

        # ulicu zatial neviem vyuzit
        self.data = self.data.drop(['ulica'], axis=1)

        # cena za m2 nie vhoda feature, kedze ju neni mozne vypocitat z pozorovani
        self.data = self.data.drop(['cena_m2'], axis=1)

        # drop riadkov kde cena je neznama/dohodu
        self.data = self.data[self.data['cena'].notna()]

        # drop extremne ceny
        self.data = self.data[600000 > self.data.cena]
        self.data = self.data[40000 < self.data.cena]

        # extremne hodnoty
        #TODO: automicka detekcia outlierov
        self.data.loc[1900 > self.data.rok_vystavby, 'rok_vystavby'] = np.NaN
        self.data.loc[50 < self.data.podlazie, 'podlazie'] = np.NaN

        self.data = self.data[17.5 > self.data.longitude]
        self.data = self.data[16.5 < self.data.longitude]

        self.data = self.data[48.4 > self.data.latitude]
        self.data = self.data[47.9 < self.data.latitude]

        # normalizuj type kurenia
        self.data.loc[~self.data.kurenie.isin(['Ustredne', 'Lokalne']), 'kurenie'] = None

        self.data.loc[self.data.energ_cert == 'nema', 'energ_cert'] = None

        self.data.loc[~self.data.garaz.isnull(), 'garaz'] = 1
        self.data.loc[self.data.garaz.isnull(), 'garaz'] = 0

        self.data.loc[~self.data.garazove_statie.isnull(), 'garazove_statie'] = 1
        self.data.loc[self.data.garazove_statie.isnull(), 'garazove_statie'] = 0

    def make_dummies_from_cat(self):

        cat_columns = ['mesto','druh','stav', 'kurenie','energ_cert', 'vytah', 'garaz', 'garazove_statie']

        self.data = pd.get_dummies(self.data, columns=cat_columns, prefix=cat_columns)

        self.data.columns = self.data.columns.str.strip()

    def make_data_matrix(self):
        self.y = self.data['cena']

        self.X = self.data.drop(['cena'], axis=1)

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(self.X, self.y, test_size=0.1, random_state=123)

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

        self.log.info(score)

        return {'loss': score, 'status': STATUS_OK}

    def optimize(self, trials, space):

        best = fmin(self.score, space, algo=tpe.suggest, max_evals=2000)
        return best

    def find_best_model(self):

        trials = Trials()

        best_params = self.optimize(trials, self.space)

        self.best_params = space_eval(self.space, best_params)

        self.log.info(self.best_params)

    def train_model(self):

        # overenie prenosu best_params
        self.xg_reg = xgb.XGBRegressor(**self.best_params)

        self.xg_reg.fit(self.X_train, self.y_train, verbose=False)

        Y_pred = self.xg_reg.predict(self.X_test)

        self.mae = mean_absolute_error(self.y_test, Y_pred)

        self.log.info(self.mae)

        self.log.info(sorted( ((v,k) for k,v in self.xg_reg.get_booster().get_score(importance_type='weight').items()), reverse=True))

        # pretrenuj finalny model na vsetkych datach
        self.xg_reg = xgb.XGBRegressor(**self.best_params)

        self.xg_reg.fit(self.X, self.y, verbose=False)

    def save_model(self):

        best_model = os.path.basename(os.path.realpath(self.best))
        best_score = int(float(best_model.split('_')[-1]))

        new_model = 'model_{}'.format(str(int(self.mae)))

        pickle.dump(self.xg_reg, open('model/{}'.format(new_model), 'wb'))

        if best_score <= self.mae:
            self.log.info('New score {} is higher than present lowest {} score!'.format(self.mae, best_score))
            return

        try:
            os.unlink(self.best)

        except FileNotFoundError:
            self.log.warning('No best soft link was found!')

        os.symlink(new_model, './model/best')

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
