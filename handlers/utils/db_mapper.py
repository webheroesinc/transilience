
import sys, os
import json


class Node(object):

    def __init__(self, data, name='root', parent=None):
        self.name		= name
        self.parent		= parent
        self.table		= None
        self.key		= None
        self.has		= None
        self.default		= None
        self.children		= {}

        for k,v in data.items():
            print "Processing key: {0} value type: {1}".format(k, type(v))
            if k.startswith('.'):
                print "Found directive"
                setattr(self, k.strip('.'), v)
            elif k.startswith('$'):
                print "Found default"
                self.default		= Node(v,k,parent=self)
            elif type(v) is dict:
                print "Child node"
                self.children[k]	= Node(v,k,parent=self)
            else:
                print "Child value"
                self.children[k]	= v

    def __getitem__(self, key):
        return self.children.get(key, self.default)

    def columns(self):
        columns		= []
        table		= self.parent.table
        for k,v in self.children.items():
            if type(v) is Node:
                print v.columns()
            elif  type(v) is str:
                columns.append("`%s`.`%s` as `%s`" % (table, k, v))
            else:
                columns.append("`%s`.`%s`" % (table, k))
        return columns

    def query(self, node):
        columns		= node.columns()
        columnstr	= ", ".join(columns)
        
        table		= node.parent.table
        key		= node.parent.key
        
        query		= """
        SELECT %s from `%s`
         WHERE `%s`.`%s` = %%s
        """ % (columnstr, table, table, key)
        return query

    def build(self, path):
        print "Getting path: {0}".format(path)
        segments	= path.strip('/').split('/')
        print "Found segments: {0}".format(segments)
        node		= self
        args		= []
        for seg in segments:
            node	= node[seg]
            if node.name.startswith('$'):
                args.append(seg)

        query		= self.query(node)
        return query, args

    def __call__(self, path):
        query, args	= self.build(path)
        return query, args

    def deobject(self):
        childs		= {}
        for k,v in self.children.items():
            childs[k]			= v.deobject() if type(v) is Node else v
        if self.default is not None:
            childs[self.default.name]	= self.default.deobject()
        return childs

    def __str__(self):
        o	= self.deobject()
        return json.dumps(o)


def load(fpath):
    with open(fpath, 'r') as f:
        data	= json.loads(f.read())
        
    return Node(data)

    # self.node('/movie/100')
    # 
    # select title, description, year, rating, length, categories.name, categories.description from movies
    #   join movie_has_category
    #        on movies.movie_id			= movie_has_category.movie_id
    #   join categories
    #        on categories.category_id		= movie_has_category.category_id
    #  where movie_id = $movie
