# -*- coding: UTF-8 -*-
from matplotlib.font_manager import FontProperties
import matplotlib.pyplot as plt
from math import log
import operator

from utils.createPlot import createPlot



def createDataSet():
	dataSet = [[0, 0, 0, 0, 'no'],						
			[0, 0, 0, 1, 'no'],
			[0, 1, 0, 1, 'yes'],
			[0, 1, 1, 0, 'yes'],
			[0, 0, 0, 0, 'no'],
			[1, 0, 0, 0, 'no'],
			[1, 0, 0, 1, 'no'],
			[1, 1, 1, 1, 'yes'],
			[1, 0, 1, 2, 'yes'],
			[1, 0, 1, 2, 'yes'],
			[2, 0, 1, 2, 'yes'],
			[2, 0, 1, 1, 'yes'],
			[2, 1, 0, 1, 'yes'],
			[2, 1, 0, 2, 'yes'],
			[2, 0, 0, 0, 'no']]
	labels = ['F1-AGE', 'F2-WORK', 'F3-HOME', 'F4-LOAN']		
	return dataSet, labels


def createTree(dataset,labels,featLabels):
	classList = [example[-1] for example in dataset]
	# classList[0]：取出第一个元素，比如'no'
	# classList.count(...)：统计这个值在整个列表中出现的次数
	# 意思是：如果列表中所有的元素都等于第一个元素，也就是说，所有样本都属于同一个类别
	if classList.count(classList[0]) == len(classList):
		return classList[0]

	# dataset[0] 表示第一个样本（第一行）；
	# 这段代码的意思是：如果当前数据集中每个样本只剩下一个字段（即只有类别标签，没有特征了），就不再划分，返回多数类作为叶子节点。
	if len(dataset[0]) == 1:
		return majorityCnt(classList)

	# 选择佳根节点
	bestFeat = chooseBestFeatureToSplit(dataset)

	bestFeatLabel = labels[bestFeat]
	featLabels.append(bestFeatLabel)
	myTree = {bestFeatLabel:{}}
	del labels[bestFeat]
	featValue = [example[bestFeat] for example in dataset]
	uniqueVals = set(featValue)
	for value in uniqueVals:
		sublabels = labels[:]
		myTree[bestFeatLabel][value] = createTree(splitDataSet(dataset,bestFeat,value),sublabels,featLabels)
	return myTree

def majorityCnt(classList):
	classCount={} #  创建一个空字典（键值对）
	for vote in classList:
		if vote not in classCount.keys():classCount[vote] = 0
		classCount[vote] += 1
	sortedclassCount = sorted(classCount.items(),key=operator.itemgetter(1),reverse=True)
	return sortedclassCount[0][0]

def chooseBestFeatureToSplit(dataset):
	numFeatures = len(dataset[0]) - 1 # 获取当前数据集的列数（特征数），减去类别标签

	#什么都没做的时候，数据集的熵
	baseEntropy = calcShannonEnt(dataset)

	bestInfoGain = 0 # 最好的信息增益
	bestFeature = -1 # 最好划分的属性

	for i in range(numFeatures): #遍历列
		featList = [example[i] for example in dataset] #取得当前列
		uniqueVals = set(featList) #去重
		newEntropy = 0 #i这一列分叉后的熵
		for val in uniqueVals:
			subDataSet = splitDataSet(dataset,i,val) # 按照第i列的val属性分叉的所有样本
			prob = len(subDataSet)/float(len(dataset))
			newEntropy += prob * calcShannonEnt(subDataSet)
		infoGain = baseEntropy - newEntropy #  计算信息增益
		if (infoGain > bestInfoGain):
			bestInfoGain = infoGain
			bestFeature = i
	return bestFeature

def splitDataSet(dataset,axis,val):
	# axis是列，val是当前列的属性值之一
	# 本方法的作用是：所有样本按照axis列中，val值进行分堆
	retDataSet = []
	for featVec in dataset: #遍历每个样本
		if featVec[axis] == val: # val是当前列的属性值之一
			reducedFeatVec = featVec[:axis] #取出当前样本 featVec 中第 0 到 axis-1 的所有特征值（不包括 axis）；
			reducedFeatVec.extend(featVec[axis+1:])#  取出当前样本 featVec 中第 axis+1 到最后的所有特征值，并把这些值拼接到 reducedFeatVec 后面；
			retDataSet.append(reducedFeatVec)
	return retDataSet
			
def calcShannonEnt(dataset):
	#  计算数据集的熵
	numexamples = len(dataset)
	labelCounts = {} #  创建一个空字典（键值对）
	for featVec in dataset:
		currentlabel = featVec[-1] #featVec[-1] 代表featVec最后一个属性
		if currentlabel not in labelCounts.keys():
			labelCounts[currentlabel] = 0
		labelCounts[currentlabel] += 1
		
	shannonEnt = 0
	for key in labelCounts:
		prop = float(labelCounts[key])/numexamples #prop是key这个标签的概率值
		shannonEnt -= prop*log(prop,2)
	return shannonEnt


if __name__ == '__main__':
	dataset, labels = createDataSet()
	featLabels = []
	myTree = createTree(dataset,labels,featLabels)
	createPlot(myTree)
	
	
	
	
	

	
	






						
