
from utils		import db_mapper

import simplejson	as json

root		= db_mapper.load('../mapper.json')
print root

print json.dumps(root('/movie/100'), indent=4)
print json.dumps(root('/movie/100/actors'), indent=4)
print json.dumps(root('/movie/100/actors/99001'), indent=4)
print json.dumps(root('/movie/100/actors/99001/age'), indent=4)
print root('/movie/100/actors/99001/name/full')

