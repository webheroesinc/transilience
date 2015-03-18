
from utils		import db_mapper

import simplejson	as json

root		= db_mapper.load('../mapper.json')
print root

roots		= root('/movie/100')
print json.dumps(roots, indent=4)
# print root('/movie/100/categories/20000/name')

