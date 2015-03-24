
import sys, os
import json

import MySQLdb		as mysqldb
import MySQLdb.cursors	as mysql_cursors

mysql_ip	= "172.17.1.108"
db		= mysqldb.connect( host		= mysql_ip,
                                   user		= "root",
                                   passwd	= "tesla",
                                   db		= "transilience",
                                   cursorclass	= mysql_cursors.DictCursor )
curs		= db.cursor()


class View(object):

    def __init__(self, data, name='root', trail=None):
        self.table		= None
        self.alias		= None
        self.name		= name
        self._directives	= {}
        self._columns		= {}
        self._segments		= []
        self._wheres		= {}

        if trail is None:
            trail		= []
        if name == 'root':
            self._trail		= []
            self._root		= None
            self._parent	= None
        else:
            self.table,_,self.alias	= data.get('.table').partition(':')
            self._trail		= trail+[self]
            self._root		= self._trail[0]
            self._parent	= self._trail[-2] if len(self._trail) > 1 else None

        for k,v in data.items():
            if k.startswith('.'):
                self.directive(k.strip('.'), v)
            elif type(v) is dict and v.get('.table') is not None:
                self._columns[k]	= View(v, name=k, trail=self._trail)
            else:
                self._columns[k]	= v

        if self._root is None:
            return

        for segment in self.directive('segments') or []:
            k		= segment.get('key')
            s		= segment.get('size')
            w		= segment.get('where')
            t		= self.alias or self.table
            if len(self._wheres):
                self._wheres[k]	= "`%s`.`%s` = %%s" % (t, w)
            else:
                self._wheres[k]	= "`%s`.`%s` = %%s" % (t, w)
            self._segments.append((k,s))

        # - build column string
        # - build join string
        columns, joins		= self.precalculate()
        self.columns		= ", ".join(columns)
        self.joins		= "\n          ".join(joins)

        root			= self._root
        self._get_query		= """
        SELECT %s
          FROM `%s` %s
          %s
         {where}
        """ % ( self.columns,
                root.table, root.alias or '',
                self.joins )

        self._update_query	= """
        UPDATE `%s` %s
          %s
           SET {set}
         {where}
        """ % ( self.table, self.alias or '',
                self.joins )

    def directive(self, key, value=None):
        print "Directive:	%s:%s" % (key,value)
        if value is None:
            return self._directives.get(key)
        else:
            self._directives[key]	= value
            return value

    def precalculate(self, columns=None):
        table		= self.alias or self.table
        clist		= ["`%s`.`%s`" % (table, self._directives.get('key'))]
        jlist		= []
        columns		= columns or self._columns
        for k,v in columns.items():
            if type(v) is View:
                c,j	= v.precalculate()	
                clist	= clist + c
                jlist	= jlist + j
            elif type(v) is dict:
                clist	= clist + self.precalculate(v)[0]
            elif type(v) in [str,unicode]:
                pass
            elif v == False:
                clist.append("`%s`.`%s`" % (table, k))
            else:
                clist.append("`%s`.`%s`" % (table, k))

        joins		= self._directives.get('has', {})
        for k,v in joins.items():
            t,_,a	= k.partition(':')
            jlist.append("JOIN `%s` `%s`\n            ON %s = %s" % ((t,a or '')+tuple(v)))

        if self._directives.get('join') is not None:
            jlist.append("JOIN `%s` %s\n            ON %s = %s" % ((self.table,self.alias or '')+tuple(self._directives.get('join'))))

        return clist, jlist

    def wheres(self):
        base_wheres	= {}
        if self._parent:
            base_wheres.update(self._parent.wheres())
        base_wheres.update(self._wheres)
        return base_wheres
    
    def query(self, params):
        # build where clause and params
        # remember filters
        # group data

        wheres		= self.wheres()
        print wheres
        where		= []
        p		= []
        for k,v in params:
            where.append(wheres[k])
            p.append(v)

        if where:
            where_str	= "WHERE "
            where_str  += "\n           AND ".join(where)
        else:
            where_str	= ""
            
        query		= self._get_query.format(where=where_str)
        
        print query, p
        return query, p

    def set(self, data):
        # if key exists
        #     add missing keys as None then pass to self.update()
        # else
        #     make a insert query
        pass

    # root.update("/movie/100", { movie data })
    def update(self, path, data):
        # get the correct view
        # verify the key(s) are present
        #   [ transaction ]
        # create update query
        # run sub updates
        #   [ transaction ]
        segments	= path.strip('/').split('/')
        update		= {}
        for name,view in self._columns.items():
            try:
                update[name]	= data[name]
            except Exception as e:
                pass

    # root.delete("/movie/100")
    def delete(self, path):
        # get the correct view
        #   [ transaction ]
        # create delete query
        # delete from has tables
        # and dependent tables
        #   [ transaction ]
        pass

    def _get(self, path):
        segments	= path.strip('/').split('/')
        print "Found segments: {0}".format(segments)
        
        fmt		= "multiple"
        filters		= []
        params		= []
        pcount		= 0
        state		= "view"
        view		= self
        while segments:
            seg		= segments.pop(0)

            if type(view.get(seg)) is View:
                state	= "view"
                
            if state == "view":
                view		= view.get(seg)
                pcount		= 0
                fmt		= "multiple"
                if len(view._segments) > 0:
                    state	= "segments"
                else:
                    state	= "filters"
            elif state == "segments":
                print "Expeting seg:	%s" % (seg,)
                var,fmt		= view._segments[pcount]
                pcount	       += 1
                params.append( (var, seg) )
                if pcount == len(view._segments):
                    state	= "filters"
            elif state == "filters":
                print "Expeting filter:	%s" % (seg,)
                filters.append(seg)

        print "Filters:		%s" % (filters,)
        query, params		= view.query(params)
        curs.execute(query, params)
        result			= view.group_data(curs.fetchall(), format=fmt)

        for f in filters:
            prev_result		= result
            for k in result.keys():
                if str(k) == f:
                    result	= result.get(k)
            if prev_result == result:
                print prev_result
                raise Exception("Endpoint does not exist: %s" % (path,))
        return result

    def group_data(self, data, format=None):
        key			= self._directives.get('key')
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

        result			= {}
        for group in groups:
            datum	= self.attach(group[0], self._columns, group)
            result[group[0][key]]	= datum

        if format == "single":
            result	= (len(result) or None) and result.popitem()[1]

        return result

    def attach(self, data, columns, rows=None):
        struct		= columns.copy()
        for k,v in struct.items():
            if v == True:
                struct[k]	= data[k]
            elif type(v) is dict:
                struct[k]	= self.attach(data,v)
            elif type(v) in [str,unicode]:
                struct[k]	= v.format(**data)
                if v.startswith(':'):
                    struct[k]	= eval(struct[k][1:])
            elif type(v) is View:
                struct[k]	= v.group_data(rows)
            elif v == False:
                del struct[k]
            else:
                struct[k]	= None
        return struct

    def breadcrumbs(self):
        return "->".join([t.name for t in self._trail])

    def get(self, k, *args):
        return self._columns.get(k,*args)

    def __call__(self, path):
        return self._get(path)

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

# SELECT `m`.`movie_id`, `m`.`movie_id`, `m`.`description`, `m`.`title`, `a`.`actor_id`, `a`.`age`, `a`.`last_name`, `a`.`actor_id`, `a`.`first_name`, `m`.`movie_id`, `m`.`rating`, `m`.`length`, `m`.`year`, `c`.`category_id`, `c`.`description`, `c`.`name`
#   FROM `movies` m
#   JOIN `movie_has_actor` mha
#     ON m.movie_id = mha.movie_id
#   JOIN `actors` a
#     ON a.actor_id = mha.actor_id
#   JOIN `movie_has_category` mhc
#     ON m.movie_id = mhc.movie_id
#   JOIN `categories` c
#     ON c.category_id = mhc.category_id

#  WHERE `m`.`movie_id` = 100;

# SELECT `a`.`actor_id`, `a`.`age`, `a`.`last_name`, `a`.`actor_id`, `a`.`first_name`
#   FROM `movies` m
#   JOIN `movie_has_actor` mha
#     ON m.movie_id = mha.movie_id
#   LEFT JOIN `actors` a
#     ON a.actor_id = mha.actor_id

#  WHERE `m`.`movie_id` = 100
#    AND `a`.`actor_id` = 99001;
