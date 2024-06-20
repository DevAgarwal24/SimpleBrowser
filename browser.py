# browser.py

import os
from url import URL

file = f'{os.path.dirname(os.path.realpath(__file__))}/demo_file.txt'

def show( body ):
    in_tag = False
    entity = ''
    skip_entity = False

    for c in body:
        if c == '<':
            in_tag = True
        elif c == '>':
            in_tag = False
        elif c == '&':
            skip_entity = True
            entity = '&'
        elif skip_entity:
            entity += c
            if entity == '&lt;':
                print('<', end="")
                skip_entity = False
                entity = ''
            elif entity == '&gt;':
                print('>', end="")
                skip_entity = False
                entity = ''
            elif entity.endswith(';'):
                print(entity, end="")
                skip_entity = False
                entity = ''
        elif not in_tag:
            print( c, end="" )

def load( url ):
    body = url.request()
    show( body )

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        load( URL( sys.argv[1] ) )
    elif len(sys.argv) == 1:
        load( URL( f'file://{file}' ))