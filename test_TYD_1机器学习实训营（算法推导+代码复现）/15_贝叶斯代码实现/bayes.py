import numpy as np
import re 
import random


def textParse(input_string):
    listofTokens = re.split(r'\W+',input_string)
    return [tok.lower() for tok in listofTokens if len(listofTokens)>2]

def creatVocablist(doclist):
    vocabSet = set([])
    for document in doclist:
        vocabSet = vocabSet|set(document)
    return list(vocabSet)
def setOfWord2Vec(vocablist,inputSet):
    #创建语料表等长的向量returnVec标识对应位置的词在输入中是否出现，如果出现标记为1，不出现标记为0
    returnVec  = [0]*len(vocablist)
    for word in inputSet:
        if word in vocablist:
            returnVec[vocablist.index(word)] = 1
    return returnVec
    
def trainNB(trainMat,trainClass):
    numTrainDocs = len(trainMat) #训练集的个数
    numWords = len(trainMat[0]) #词的个数

    # 垃圾邮件的概率：
    # trainClass是通过0、1标记的。所以sum就是垃圾邮件的个数
    p1 = sum(trainClass)/float(numTrainDocs)

    p0Num = np.ones((numWords)) #（0正常邮件）定义语料长度的向量，对应位置的词出现次数初始化为1
    p1Num = np.ones((numWords)) #（1垃圾邮件）定义语料长度的向量，对应位置的词出现次数初始化为1

    p0Denom = 2 #（0正常邮件）总词数
    p1Denom = 2 #（1垃圾邮件）总次数

    # 遍历每片文章
    for i in range(numTrainDocs):
        if trainClass[i] == 1:
            #垃圾邮件
            p1Num += trainMat[i] #这里是向量相加，对应位置的1相加。统计词频
            p1Denom += sum(trainMat[i]) #这里是统计总词数目
        else:
            #正常邮件
            p0Num += trainMat[i]
            p0Denom += sum(trainMat[i])

    p1Vec = np.log(p1Num/p1Denom) #垃圾邮件中，每个词的概率向量
    p0Vec = np.log(p0Num/p0Denom) #正常邮件中，每个词的概率向量

    return p0Vec,p1Vec,p1
    
def classifyNB(wordVec,p0Vec,p1Vec,p1_class):

    # P(h+/D) = P(h+) * P(D|h+) / P(D)
    # P(h+/D) = P(h+) * P(D|h+) / P(D)
    # 两边取对数。
    # 根据朴素贝叶斯的假设，
    # 其中log(P(D|h+))=log(P(D1|h+)*P(D1|h+)***P(Dn|h+))
    #                =log(P(D1|h+))+log(P(D2|h+))+...+log(P(Dn|h+))
    # 只是要比较大小。所以只求分子部分，以下/P(D)不计算
    p1 = np.log(p1_class) + sum(wordVec*p1Vec)
    p0_class = 1.0-p1_class
    p0 = np.log(p0_class) + sum(wordVec*p0Vec)
    if p0>p1:
        return 0
    else:
        return 1
    
       


def spam():
    doclist = []
    classlist = []
    for i in range(1,26):
        wordlist = textParse(open('email/spam/%d.txt'%i,'r',encoding='latin1').read())
        doclist.append(wordlist)
        classlist.append(1) #1表示垃圾邮件
        
        wordlist = textParse(open('email/ham/%d.txt'%i,'r',encoding='latin1').read())
        doclist.append(wordlist)
        classlist.append(0) #1表示垃圾邮件
        
    vocablist = creatVocablist(doclist)

    trainSet = list(range(50)) #训练集
    testSet = []       #测试集
    for i in range(10): #从训练集的50个里面随机选10个出来放到测试集，然后吧训练集里删掉
        randIndex = int(random.uniform(0,len(trainSet)))
        testSet.append(trainSet[randIndex])
        del (trainSet[randIndex])

    trainMat = [] #训练集的向量
    trainClass = [] #训练集对应的类别
    for docIndex in trainSet: #把训练集的50个都遍历一遍
        trainMat.append(setOfWord2Vec(vocablist,doclist[docIndex]))
        trainClass.append(classlist[docIndex])

    # 训练
    p0Vec,p1Vec,p1 = trainNB(np.array(trainMat),np.array(trainClass)) #训练

    errorCount = 0
    for docIndex in testSet:
        wordVec = setOfWord2Vec(vocablist,doclist[docIndex])

        # 朴素贝叶斯预测测试邮件是否是垃圾邮件
        if classifyNB(np.array(wordVec),p0Vec,p1Vec,p1) != classlist[docIndex]:
            errorCount+=1
    print ('当前测试了10个样本，只预测错了：',errorCount)

if __name__ == '__main__':
    spam()
        
    
    
    
    
    
    
    
    
    
    
        
