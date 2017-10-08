import json, sys, pymongo, requests
from gensim import models
from itertools import takewhile

model = models.KeyedVectors.load_word2vec_format('../med400.model.bin', binary=True)
stopwords = json.load(open('stopwords.json','r'))
class KCEM(object):
	"""docstring for KCEM"""
	def __init__(self, file, uri=None):
		from pymongo import MongoClient
		self.client = MongoClient('mongodb://172.17.0.17:27017')
		self.db = self.client['nlp']
		self.kcm_collect = self.db['kcm_new']
		self.kcem_collect = self.db['kcem']
		self.file = file

	def insert(self):
		with open(self.file, 'r') as f:
			data = json.load(f)
			# if len(set([i['key'] for i in data])) != len(data):
			# 	raise Exception("Has duplicate key")
			# 	print("Has duplicate key")
			record = {}
			for i in data:
				if i['key'] not in record:
					record[i['key']] = i['value']
				else:
					print(i)
					print('==============')
					print(record[i['key']])
			self.kcm_collect.insert(data)
			self.kcm_collect.create_index([("key", pymongo.HASHED)])			

	def get(self, keyword, kem_topn_num):
		result = self.kcem_collect.find({'key':keyword}, {'value':1, '_id':False}).limit(1)
		if result.count()==0:
			kcm_lists = []
			kcm = self.kcm_collect.find({"key":keyword}, {'value':1, '_id':False}).limit(1)
			kcm_lists.append(set(list(kcm)[0]['value']))

			found = 1
			notfound = 0
			for kemtopn in requests.get('http://140.120.13.244:10000/kem/?keyword={}&num={}'.format(keyword, kem_topn_num)).json():
				# print(kemtopn)
				kcm = self.kcm_collect.find({"key":kemtopn[0]}, {'value':1, '_id':False}).limit(1)
				if kcm.count() == 0:
					notfound += 1
					print("{} not found {}".format(kemtopn[0], notfound))
					continue
				found += 1

				kcm_lists.append(set(list(kcm)[0]['value']))

			result={}
			for kcm_list in kcm_lists:#統計出現的字
				for word in kcm_list:
					result[word] = result.setdefault(word, 0) + 1.0/float(found)

			result = sorted(result.items(), key = lambda x: -x[1])
			result = [i for i in result if i not in stopwords and len(i) > 1]
			print(result)
			self.pointer = 0
			def take(x):
				if result[self.pointer][1] < result[4][1]:
					return False
				else:
					self.pointer += 1
					return True

			def cosSimilarity(x):
				try:
					print(x, model.similarity(keyword, x[0]))
					return (x[0], model.similarity(keyword, x[0]))
				except Exception as e:
					pass

				
			result = list(takewhile(take, result))
			result = list(map(cosSimilarity, result))
			result = [i for i in result if i != None]
			result = sorted(result, key=lambda x:-x[1])
			return result

		return dict(list(result)[0])['value'][:10]

if __name__ == '__main__':
	k = KCEM(sys.argv[1])
	if len(sys.argv) == 3 and sys.argv[2] == 'query':
		while True:
			keyword = input("please input the keyword you want to query:")
			number = input("please input the amout you want to query:")
			print(k.get(keyword, number))
			
	elif len(sys.argv) > 3:
		print(k.get(sys.argv[2], sys.argv[3]))
	else:
		k.insert()
