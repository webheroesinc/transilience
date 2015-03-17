
from utils		import db_mapper

import simplejson	as json
import MySQLdb		as mysqldb
import MySQLdb.cursors	as mysql_cursors

mysql_ip	= "172.17.1.13"
db		= mysqldb.connect( host		= mysql_ip,
                                   user		= "root",
                                   passwd	= "tesla",
                                   db		= "transilience",
                                   cursorclass	= mysql_cursors.DictCursor )
curs		= db.cursor()

root		= db_mapper.load('../mapper.json')

# print root

data		= json.loads(str(root))
print json.dumps(data, indent=4)

query, args		= root('/movie/100')
print query

curs.execute(query, args)
print json.dumps(curs.fetchall(), indent=4)

# print root('/movie/100/categories/20000/name')

