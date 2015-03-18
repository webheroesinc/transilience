
import sys, os
import json

import MySQLdb		as mysqldb
import MySQLdb.cursors	as mysql_cursors

mysql_ip	= "172.17.1.13"
db		= mysqldb.connect( host		= mysql_ip,
                                   user		= "root",
                                   passwd	= "tesla",
                                   db		= "transilience",
                                   cursorclass	= mysql_cursors.DictCursor )
curs		= db.cursor()


class View(object):

    def __init__(self, data, name='root', parents=None):
        self.name		= name
        self._parents		= parents or []
        self._directives	= {}
        self._columns		= {}
        self._params		= {}

        for k,v in data.items():
            if k.startswith('.'):
                print "Directive:	%s" % (k,)
                if k == ".table":
                    self.table,_,self.alias	= v.partition(':')
                elif k == ".segments":
                    segs		= []
                    for var in v:
                        var,_,t		= var.partition(':')
                        segs.append((var,t))
                    v			= segs
                d			= k.strip('.')
                self._directives[d]	= v
                
            elif type(v) is dict and v.get('.table') is not None:
                print "Sub table:	%s" % (k,)
                self._columns[k]	= View(v,k,parents=self._parents+[self])
            else:
                print "Column value:	%s => %s" % (k,v)
                self._columns[k]	= v


    def columns(self, columns=None):
        table		= self.alias or self.table
        clist		= ["`%s`.`%s`" % (table, self._directives.get('key'))]
        jlist		= []
        columns		= columns or self._columns
        for k,v in columns.items():
            if type(v) is View:
                c,j	= v.columns()	
                clist	= clist + c
                jlist	= jlist + j
            elif type(v) is dict:
                clist	= clist + self.columns(v)[0]
            elif type(v) in [str,unicode]:
                clist.append("`%s`.`%s` as `%s`" % (table, k, v))
            else:
                clist.append("`%s`.`%s`" % (table, k))

        joins		= self._directives.get('has', {})
        for k,v in joins.items():
            t,_,a	= k.partition(':')
            jlist.append("JOIN `%s` %s ON %s = %s" % ((t,a or '')+tuple(v)))

        if self._directives.get('join') is not None:
            jlist.append("JOIN `%s` %s ON %s = %s" % ((self.table,self.alias or '')+tuple(self._directives.get('join'))))

        return clist, jlist

    def query(self):
        columns, joins	= self.columns()
        columnstr	= ", ".join(columns)
        joinsstr	= "\n          ".join(joins)
        
        table		= self.table
        key		= self._directives.get('key')
        where		= self._directives.get('where').keys()[0]
        
        query		= """
        SELECT %s from `%s` %s
          %s 
         WHERE `%s`.`%s` = %%s
        """ % (columnstr, table, self.alias or '', joinsstr, self.alias or table, where)
        print query
        return query

    def build(self, path):
        segments	= path.strip('/').split('/')
        print "Found segments: {0}".format(segments)

        # Start off with the list of root views
        # If segments: use only that view
        # For all root views: build querys
        fmt		= self._directives.get('format', 'list')
        if len(segments):
            seg		= segments.pop(0)
            view	= root_view	= self.get(seg)
            while segments:
                if view is not None:
                    for var,fmt in view.segments():
                        view.param(var, (len(segments) or None) and segments.pop(0))
                else:
                    raise Exception("Endpoint does not exist: %s" % (path,))
                if segments:
                    view	= view.get(segments.pop(0))
            
            curs.execute( root_view.query(), tuple(root_view._params.values()) )
            result		= root_view.group_data(curs.fetchall(), format=fmt)
        else:
            for root,root_view in self._columns.items():
                curs.execute( root_view.query(), tuple(root_view._params.values()) )
                roots[root]	= root_view.group_data(curs.fetchall(), format=fmt)
            
        return result

    def group_data(self, data, format=None):
        format			= format if format is not None else self._directives.get('format')
        key			= self._directives.get('key')
        if type(self._columns.get(key)) in [str,unicode]:
            key			= self._columns.get(key)
        key_id			= None
        groups			= []
        for row in data:
            if key_id != row[key]:
                if key_id is not None:
                    groups.append(group)
                group		= []
                key_id		= row[key]
            group.append(row)
        groups.append(group)

        rows			= []
        for group in groups:
            datum	= self.attach(group[0], self._columns, group)
            rows.append( datum )

        if format == "dict":
            result	= (len(rows) or None) and rows.pop(0)
        else:
            result	= rows

        return result

    def attach(self, data, columns, rows=None):
        struct		= columns.copy()
        for k,v in struct.items():
            if v == True:
                struct[k]	= data[k]
            elif type(v) is dict:
                struct[k]	= self.attach(data,v)
            elif type(v) in [str,unicode]:
                struct[v]	= data[v]
                del struct[k]
            elif type(v) is View:
                struct[k]	= v.group_data(rows)
            else:
                struct[k]	= None
        return struct

    def param(self, k, v):
        self._params[k]	= v

    def get(self, k, *args):
        return self._columns.get(k,*args)

    def segments(self):
        return self._directives.get('segments', [])
                
    def __call__(self, path):
        return self.build(path)

    def format(self):
        fobj		= {}
        for k,v in self._columns.items():
            if type(v) is View:
                fobj['View('+k+')']	= v.format()
            else:
                fobj[k]			= v
        return fobj
                
    def __str__(self):
        return json.dumps(self.format(), indent=4)

    
def load(fpath):
    with open(fpath, 'r') as f:
        data	= json.loads(f.read())
        
    return View(data)

    # self.node('/movie/100')
    # 
    # select title, description, year, rating, length, categories.name, categories.description from movies
    #   join movie_has_category
    #        on movies.movie_id			= movie_has_category.movie_id
    #   join categories
    #        on categories.category_id		= movie_has_category.category_id
    #  where movie_id = $movie
    # 
    # select title, description, year, rating, length, categories.name, categories.description from movies
    #   join categories
    #        on categories.movie_id		= movies.movie_id
    #  where movie_id = $movie
    # 
    # select title, description, year, rating, length, categories.name, categories.description from movies
    #   join categories
    #        on categories.category_id		= movies.category_id
    #  where movie_id = $movie
