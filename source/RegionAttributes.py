import json

class RegionAttributes:
	def __init__(self, name="", description="", data = []):
		self.name = name
		self.description = description
		self.data = data  #array of { name: ... type: [boolean, number, string, keyword]  min: max: values: [] }

	def save(self):
		return self.__dict__

	def saveToFile(self, filename):
		data = self.__dict__

		for field in data:
			for i in ['min', 'max', 'keywords']:
				if data[i] == '':
					data.pop(i, None)
		
		str = json.dumps(data, indent=1)
		file = open(filename, "w")
		file.write(str)
		file.close()

	def loadFromFile(self, filename):
		file = open(filename, "r")
		try:
			data = json.load(file)
			for field in data:
				if not 'min' in data:
					data['min'] = '';
				if not 'max' in data:
					data['max'] = '';
				if not 'keuwords' in data:
					data['keywords'] = []

		except json.JSONDecodeError as e:
			raise Exception(str(e))
		
		try:
			self.name = data['name']
			self.description = data['description']
			self.data = data['data']

		except:
			raise Exception("The custo data file header has not the correct format")

	def has(self, fieldName):
		for field in self.data:
			if field['name'] == fieldName:
				return True
		return False


