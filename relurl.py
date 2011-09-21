import urlparse
import sys
import posixpath

def relurl(target,base):
    base=urlparse.urlparse(base)
    target=urlparse.urlparse(target)
    if base.netloc != target.netloc:
        raise ValueError('target and base netlocs do not match')
    base_dir='.'+posixpath.dirname(base.path)
    target='.'+target.path
    return posixpath.relpath(target,start=base_dir)

tests=[
    ('http://www.example.com/images.html','http://www.example.com/faq/index.html','../images.html'),
    ('http://google.com','http://google.com','.'),
    ('http://google.com','http://google.com/','.'),
    ('http://google.com/','http://google.com','.'),
    ('http://google.com/','http://google.com/','.'), 
    ('http://google.com/index.html','http://google.com/','index.html'),
    ('http://google.com/index.html','http://google.com/index.html','index.html'), 
    ]

for target,base,answer in tests:
    try:
        result=relurl(target,base)
    except ValueError as err:
        print('{t!r},{b!r} --> {e}'.format(t=target,b=base,e=err))
    else:
        if result==answer:
            print('{t!r},{b!r} --> PASS'.format(t=target,b=base))
        else:
            print('{t!r},{b!r} --> {r!r} != {a!r}'.format(
                t=target,b=base,r=result,a=answer))
