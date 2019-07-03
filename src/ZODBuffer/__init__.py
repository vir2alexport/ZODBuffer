import os
import re
import sys
import time

from ZODB import FileStorage, DB

import zc.bz2storage
import transaction


class ZODBuffer():
	#	ZODBuffer class is a buffers class for ZODB
	#	The goal is to split the data between the different database files
	#	For example, if you have about 5GB data growing yearly, you want to split it to small fs files
	#	so your http users could download small packs of specific data they want to monitor without overloading 
	#	server too much on every fs open big file. You can set the delimeter to split objects at specific size
	def __init__(self, objects, delimeter = 100):
		self._timer = str(int(time.time()))
		self.rootofroots = {}
		self.objects_counter = len(objects.items())
		self.objects = objects
		if 0 <= delimeter < self.objects_counter:
			self.delimeter = delimeter
	
	
	def CreateDatabases(self, dbname, prefix = 'bf', exclud = '[$]', rootofrootsName = 'RootOfRoots'):
		self.dbname = dbname
		self.rootofrootsName = rootofrootsName
		pages = 1
		counter = 0
		self.fname = self.AddNewTable(self.dbname, pages)
		for key,val in self.objects.items():
			if counter > 1 and counter % self.delimeter == 0:
				pages = pages + 1
				counter = 1
				self.CloseDB()
				self.fname = self.AddNewTable(self.dbname, pages)	#	create new database .fs file for each buffer
			#	INSERT INTO NEW TABLE
			tmpkey = re.sub(exclud, '', key)		#	remove forbidden symbols from the key
			bfname = prefix + tmpkey				#	forming unique buffer name
			self.root[bfname] = {self._timer:val}	#	the actual writing of the data to the corresponding file
			self.SetRootOfRoots(tmpkey, prefix, counter)	#	form the database of databases
			counter = counter + 1
		self.CloseDB()
		#	create and save the database of databases and close the connection
		self.InitDB(rootofrootsName)
		self.root[rootofrootsName] = self.rootofroots
		self.CloseDB()
	
	
	def SetRootOfRoots(self, key, prefix, counter):
		if 'symbols' in self.rootofroots[self.fname]:
			self.rootofroots[self.fname]['symbols'] = key +','+ self.rootofroots[self.fname]['symbols']
		else:
			self.rootofroots[self.fname]['symbols'] = key
		if 'tables' in self.rootofroots[self.fname]:
			self.rootofroots[self.fname]['tables'] = prefix+ key +','+ self.rootofroots[self.fname]['tables']
		else:
			self.rootofroots[self.fname]['tables'] = prefix+ key
		self.rootofroots[self.fname]['counter'] = counter
	
	
	def InitDB(self, fname):
		#	create storage from compressed data
		self.storage = zc.bz2storage.Bz2Storage(FileStorage.FileStorage(fname+'.fs'))
		#	create DB that uses our storage
		self.db = DB(self.storage)
		#	open DB connection object
		self.connection = self.db.open()
		#	get the root access
		self.root = self.connection.root()
	
	
	def AddNewTable(self, text, pages):
		self.fname = text + str(pages)
		self.InitDB(self.fname)
		self.rootofroots[self.fname] = {}
		self.rootofroots[self.fname]['fname'] = self.fname
		return self.fname
	
	
	def CloseDB(self):
		transaction.commit()
		print(self.root.items())
		self.connection.close()
		self.db.close()
		self.storage.close()
	
	
	def DropTables(self, folder = '/home/ubuntu/qpserver/'):
		self.initDB(self.rootofrootsName)
		for fname in self.root[self.rootofrootsName]:
			os.system('rm -rf '+ folder + fname+'.*')
			os.system('rm -rf '+ folder + self.rootofrootsName +'.*')
		self.closeDB()