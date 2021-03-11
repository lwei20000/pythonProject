import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from sklearn.cluster import KMeans

from sklearn import ensemble
from sklearn.ensemble import BaggingClassifier, RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV
from sklearn import metrics
#from sklearn import cross_validation, metrics
#from sklearn.grid_search import GridSearchCV

from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from datetime import datetime
import numpy as np
import time
import pdb

#def baggingClassify(train_x, train_y, test_x, test_y):
#    ####gradboost
#    params = {'n_estimators': 100, 'max_depth': 4, 'min_samples_split': 1,
#              'learning_rate': 0.01, 'loss': 'ls'}
#    clf_bagging = BaggingClassifier(n_estimators=200)
#    clf_bagging.fit(train_x, train_y)
#    y_pred = clf_bagging.predict(test_x)
#    y_predprob= clf_bagging.predict_proba(test_x)
#    acc = accuracy_score(test_y, y_pred)
#    print("%s n_estimators = %d, random forest accuracy:%f" % (datetime.now(), 200, acc))
#    return acc, y_predprob


def RandomForestClassify(train_x, train_y, test_x, test_y):
    ####random forest
    '''
    param_grid = { 
        'n_estimators': [100, 200, 500],
        'max_features': ['auto', 'sqrt', 'log2'],
        'max_depth' : [4,5,6,7,8],
        'criterion' :['gini', 'entropy'],
        #'min_samples_leaf': [1, 2, 4],
        #'min_samples_split': [2, 5, 10]
    }
    clf_RDF = GridSearchCV(estimator=RandomForestClassifier(random_state=42), param_grid=param_grid, cv=5)
    clf_RDF.fit(train_x, train_y)
    print(clf_RDF.best_params_)
    '''
    #best {'criterion': 'entropy', 'max_depth': 8, 'max_features': 'log2', 'n_estimators': 500}
    clf_RDF = RandomForestClassifier(n_estimators = 500, 
                                max_features = 'log2', 
                                max_depth = 8,
                                criterion = 'entropy',
                                random_state = 42)

    clf_RDF.fit(train_x, train_y)
    y_pred = clf_RDF.predict(test_x)
    y_predprob= clf_RDF.predict_proba(test_x)
    acc = accuracy_score(test_y, y_pred)
    print("%s n_estimators = %d, random forest accuracy:%f" % (datetime.now(), 200, acc))
    return acc, y_predprob, clf_RDF

def Adaboost(train_x, train_y, test_x, test_y):
    ###adaboost, svm
    '''
    params_grid = {'n_estimators': [50, 100,
        "learning_rate": [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2],
    }
    svc=SVC(probability=True, kernel='linear')
    clf_adaboost = GridSearchCV(AdaBoostClassifier(base_estimator=svc), params_grid)
    clf_adaboost.fit(train_x, train_y)
    print(clf_adaboost.best_params_)
    '''
    #{'learning_rate': 0.05, 'n_estimators': 200}
    svc=SVC(probability=True, kernel='linear')
    clf_adaboost = AdaBoostClassifier(base_estimator=svc, learning_rate=0.05, n_estimators=200)
    clf_adaboost.fit(train_x, train_y)
    y_pred = clf_adaboost.predict(test_x)
    y_predprob = clf_adaboost.predict_proba(test_x)
    acc = accuracy_score(test_y,y_pred)
    print("%s n_estimators = %d, random forest accuracy:%f" % (datetime.now(), 200, acc))
    return acc, y_predprob, clf_adaboost
    

def gbdt(train_x, train_y, test_x, test_y):
    ########gbdt
    '''
    param_grid = {
        "loss":["deviance"],
        "learning_rate": [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2],
        "min_samples_split": np.linspace(0.1, 0.5, 12),
        "min_samples_leaf": np.linspace(0.1, 0.5, 12),
        "max_depth":[3,5,8],
        "max_features":["log2","sqrt"],
        "criterion": ["friedman_mse",  "mae"],
        "subsample":[0.5, 0.618, 0.8, 0.85, 0.9, 0.95, 1.0],
        "n_estimators":[10]
    }
    param_grid = {
        'n_estimators': [100, 200, 500],
        'max_features': ['auto', 'sqrt', 'log2'],
        'max_depth' : [4,5,6,7,8],
        #'criterion' :['gini', 'entropy'],
        #'min_samples_leaf': [1, 2, 4],
        #'min_samples_split': [2, 5, 10]
        }

    clf_gbdt = GridSearchCV(GradientBoostingClassifier(), param_grid, cv=10, n_jobs=-1)
    clf_gbdt.fit(train_x, train_y)
    print(clf_gbdt.best_params_)
    '''
    # {'max_depth': 4, 'max_features': 'log2', 'n_estimators': 500}
    clf_gbdt = GradientBoostingClassifier(n_estimators=500, max_depth=4, \
            max_features='log2',learning_rate=0.2)
    clf_gbdt.fit(train_x, train_y)
    y_pred = clf_gbdt.predict(test_x)
    y_predprob = clf_gbdt.predict_proba(test_x)

    acc = accuracy_score(test_y, y_pred)
    print("%s n_estimators = %s, random forest accuracy:%f" % (datetime.now(), "GBDT",  acc))
    return acc, y_predprob, clf_gbdt

def ensemble_mean(prob_RDF, prob_ada, prob_gbdt, test_y):
    mean_prob = (prob_RDF + prob_ada + prob_gbdt)/3
    y_pred = np.argmax(mean_prob, axis=1)
    acc = accuracy_score(test_y, y_pred)
    print("ensemble mean result is:%f" % (acc))
    return acc, y_pred

def ensemble_vote(clf_RDF, clf_adaboost, clf_gbdt, train_x, train_y, test_x, test_y):

    voting_est = ensemble.VotingClassifier(estimators = [('rf', clf_RDF), \
                                        ('gbm', clf_adaboost), ('et', clf_gbdt)], \
                                        voting = 'soft', weights = [3,5,2], \
                                        n_jobs = 50)
    voting_est.fit(train_x, train_y)
    y_pred = voting_est.predict(test_x)
    acc = accuracy_score(test_y, y_pred)

    print("vote accuracy:%f" % (acc))
    return acc, y_pred

def draw_org(x_train):
    fig, ax_big = plt.subplots()
    for i in range(25):
        x = x_train[i]
        x = x.reshape([8,8])
        ax = fig.add_subplot(5, 5, i+1) 
        ax.imshow(x, cmap=plt.cm.gray)
        ax.set_xticks([])              
        ax.set_yticks([])
    ax_big.set_xticks([])                                   
    # 隐藏坐标轴刻度
    ax_big.set_yticks([])
    plt.show()
    plt.savefig("org.png", dpi=150)
    plt.close()

def draw_result(pred_y, test_y):
    #https://www.kaggle.com/gauravduttakiit/digit-recognizer-using-gradientboostingclassifier
    cm = metrics.confusion_matrix(test_y, pred_y)
    plt.figure(figsize=(9,9))
    plt.imshow(cm,cmap='rainbow_r')
    plt.title("Confusion Matrix for MNIST Data")
    plt.xticks(np.arange(10))
    plt.yticks(np.arange(10))
    plt.ylabel('Actual Label')
    plt.xlabel('Predicted Label')
    plt.colorbar()
    width,height = cm.shape
    for x in range(width):
        for y in range(height):
            plt.annotate(str(cm[x][y]),xy=(y,x),horizontalalignment='center',verticalalignment='center')
    plt.show()
    plt.savefig("CM_MINIST.png")
    plt.clf()
    plt.close()

if __name__=="__main__":
    print('导入数据')
    pdb.set_trace()
    digits = load_digits()
    data = digits.data
    label = digits.target

    train_x = data[:1000, :]
    train_y = label[:1000]
    test_x = data[1000:, :]
    test_y = label[1000:]
    draw_org(train_x)
    print("start Gradient Boosting")
#    pdb.set_trace()
    StartTime = time.clock()
    #train_x, test_x, train_y, test_y = train_test_split(data, label, test_size=0.3)
    acc_RDF, prob_RDF, clf_RDF = RandomForestClassify(train_x, train_y, test_x, test_y)
    acc_ada, prob_ada, clf_adaboost = Adaboost(train_x, train_y, test_x, test_y)
    acc_gbdt, prob_gbdt, clf_gbdt = gbdt(train_x, train_y, test_x, test_y)
    acc, pred_y = ensemble_mean(prob_RDF, prob_ada, prob_gbdt, test_y)
    acc, pred_y = ensemble_vote(clf_RDF, clf_adaboost, clf_gbdt, train_x, train_y, test_x, test_y)
    draw_result(pred_y, test_y)
    EndTime = time.clock()
    print('Total time %.2f s' % (EndTime - StartTime))
 
