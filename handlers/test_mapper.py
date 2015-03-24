
from utils		import db_mapper

import simplejson	as json

root		= db_mapper.load('../mapper.json')
movie		= root.get('movie')
actor		= movie.get('actors')

print actor._segments

# print root
# print json.dumps(root('/movie'), indent=4)
# print json.dumps(root('/movie/101/categories'), indent=4)
# print json.dumps(root('/movie/100/actors/99001/age'), indent=4)
print root('/movie/100/actors/99001/name/full')

print actor._root.table
print actor._query
