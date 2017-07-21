#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2017-07-18

@author: Joschi <josua.krause@gmail.com>

This package provides a customizable survey user interface.
"""
from __future__ import print_function
from __future__ import division

import os
import sys
import json
import math
import argparse
import threading

from quick_server import create_server, msg, setup_restart, Response, PreventDefaultResponse

try:
    unicode = unicode
except NameError:
    # python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str, bytes)
else:
    # python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring


__version__ = "0.0.3"


def get_server(addr, port, full_spec, output):
    spec, title, prefix = full_spec
    server = create_server((addr, port))

    prefix = '/' + (os.path.basename(os.path.normpath(server.base_path)) if prefix is None else prefix)

    server.link_empty_favicon_fallback()
    server.favicon_everywhere = True

    server.suppress_noise = True
    server.report_slow_requests = True

    token_lock = threading.RLock()

    def token_obj(token):
        with token_lock:
            res = server.get_token_obj(token)
            tfile = os.path.join(output, "{0}.json".format(token))
            if not len(res.keys()) and os.path.exists(tfile):
                with open(tfile, 'r') as fin:
                    res = json.load(fin)
            return res

    def write_token(token, tobj):
        with token_lock:
            if not os.path.exists(output):
                os.makedirs(output)
            with open(os.path.join(output, "{0}.json".format(token)), 'w') as out:
                json.dump(tobj, fp=out, sort_keys=True, indent=2)

    @server.text_get(prefix + '/img/', 1)
    def text_file(req, args):
        new_name = args["paths"][0]
        fname = get_rev_file(new_name)
        if fname is None:
            return None
        with open(fname, 'r') as f_in:
            ext = get_extension(fname)
            mime = {
                "svg": "svg+xml",
                "jpg": "jpeg",
            }.get(ext, ext)
            return Response(f_in.read(), ctype='image/{0}'.format(mime))

    @server.text_get(prefix + '/', 0)
    def text_index(req, args):
        return post_index(req, args)

    @server.text_post(prefix + '/', 0)
    def post_index(req, args):
        if "token" not in args["query"]:
            with token_lock:
                url = "{0}/?pix=0&token={1}".format(prefix, server.create_token())
                req.send_response(307, "Ready to go!")
                req.send_header("Location", url)
                req.end_headers()
                raise PreventDefaultResponse()
        token = args["query"]["token"]
        with token_lock:
            tobj = token_obj(token)
            if "post" in args:

                def set_value(o, k, v):
                    if "/" not in k:
                        o[k] = v
                        return
                    kix = k.index("/")
                    tmp = k[:kix]
                    if tmp not in o:
                        o[tmp] = {}
                    set_value(o[tmp], k[kix + 1:], v)

                pobj = args["post"]
                pid = pobj["_pid"]
                for (k, v) in pobj.items():
                    if k == "_pid":
                        continue
                    if k.startswith("_nop"):
                        continue
                    set_value(tobj, "{0}/{1}".format(pid, k), v)
                write_token(token, tobj)
        pix = int(args["query"]["pix"])
        url = "?pix={0}&token={1}".format(pix + 1, token)
        res, _pid, last_page = create_page(spec, pix, url, token, tobj, title)
        if last_page:
            msg("{0} finished!", token)
        return Response(res, ctype="text/html")

    dry_run(spec)
    return server, prefix


FILE_BASE = "."
def set_file_base(fbase):
    global FILE_BASE
    FILE_BASE = fbase


FILE_LOOKUP = {}
FILE_REV_LOOKUP = {}
FILE_NAME_IX = 0
FILE_LOCK = threading.RLock()
def get_file(fname):
    global FILE_NAME_IX
    fname = os.path.join(FILE_BASE, fname)
    if fname not in FILE_LOOKUP:
        if not os.path.exists(fname):
            raise ValueError("cannot find file: '{0}'".format(fname))
        with FILE_LOCK:
            new_name = "{0}.{1}".format(FILE_NAME_IX, get_extension(fname))
            FILE_NAME_IX += 1
            FILE_LOOKUP[fname] = new_name
            FILE_REV_LOOKUP[new_name] = fname
    return FILE_LOOKUP[fname]


def get_extension(fname):
    ext_ix = fname.rfind('.')
    return fname[ext_ix + 1:]

def get_rev_file(new_name):
    return FILE_REV_LOOKUP.get(new_name, None)


def dry_run(spec):
    pass
    # pids = set()
    # has_last_page = False
    # for (pix, s) in enumerate(spec):
    #     _res, pid, last_page = create_page(spec, pix, "NOPE", "ANON", {}, "DRY")
    #     if not has_last_page: # only check reachable pages
    #         if pid in pids:
    #             raise ValueError("duplicate pid '{0}'".format(pid))
    #         pids.add(pid)
    #     if last_page:
    #         has_last_page = True
    # if not has_last_page:
    #     raise ValueError("survey has no last page!")


class HTMLPage(object):
    def __init__(self, base, url):
        self._base = base
        self._url = url
        self._content = ""

    def append(self, s):
        self._content += str(s)

    def __iadd__(self, s):
        self.append(s)
        return self

    def finish(self, **args):
        return self._base.format(url=self._url, content=self._content, **args)


class Tag(object):
    def __init__(self, page, name, styles={}, attrs={}):
        self._page = page
        self._name = name
        self._styles = styles
        self._attrs = attrs

    def _get_styles(self):
        if not len(self._styles.items()):
            return ""
        return " style=\"{0}\"".format('; '.join([
            "{0}: {1}".format(k, v)
            for (k, v) in self._styles.items()
            if v is not None
        ]))

    def _get_attrs(self):
        if not len(self._attrs.items()):
            return ""
        return " {0}".format(' '.join([
            "{0}=\"{1}\"".format(k, v)
            for (k, v) in self._attrs.items()
            if v is not None
        ]))

    def no_close(self):
        self._page += "<{0}{1}{2}>".format(
            self._name, self._get_styles(), self._get_attrs())

    def append(self, s):
        self._page.append(s)

    def __iadd__(self, s):
        self._page += str(s)
        return self

    def __enter__(self):
        self.no_close()
        return self

    def __exit__(self, type, value, traceback):
        self._page += "</{0}>".format(self._name)
        return False


def create_page(spec, pix, url, token, tobj, title):
    content = HTMLPage("""<!DOCTYPE html>
    <head>
        <title>{title}</title>
        <style>
            * {{
                box-sizing: border-box;
                font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;
                font-size: 16px;
                line-height: 1.42857143;
            }}
        </style>
    </head>
    <body style="height: 100vh; width: 100vw; margin: 0; padding: 0;">
        <div style="display: flex; align-items: center; justify-content: center; height: 100%; flex-direction: column;">
            <div style="flex-grow: 0; flex-shrink: 0;">
                <form id="main_form" action="{url}" method="post">
                {content}
                <input type="hidden" value="{pid}" name="_pid"></input>
                </form>
            </div>
            <div style="flex-grow: 0.5; flex-shrink: 1;">
            </div>
        </div>
        <script>
            {js}
            document.getElementById("main_form").onsubmit = () => {{
                window.onbeforeunload = null;
            }};
        </script>
    </body>
    """, url)
    page = spec[pix]
    pt = page.get("type", "plain")
    var = page["vars"].copy()
    var["token"] = token

    def f(s):
        return str(s).format(**var)

    pid = f(page.get("pid", "p{0}".format(pix)))

    def flatten_items(tobj, prefix, query):
        qu = query.split('/', 1) if query is not None else [ None ]
        cq = qu[0]
        fq = qu[1] if len(qu) > 1 else None
        for (k, v) in tobj.items():
            if cq is not None and k != cq:
                continue
            key = "{0}{1}".format(prefix, k) if cq is None else prefix
            if isinstance(v, dict):
                for ii in flatten_items(v, "{0}/".format(key) if key != prefix else key, fq):
                    yield ii
            else:
                yield (key, v)

    var.update(dict(flatten_items(tobj, "cur/", pid)))

    def interpret_lines(content, lines):
        if isinstance(lines, basestring):
            with open(f(lines), "r") as f_in:
                lines = f_in.readlines()
        for line in lines:
            if isinstance(line, basestring):
                with Tag(content, "p") as p:
                    p.append(f(line))
                continue
            lt, text, lid = line
            if lt == 'img':
                Tag(content, "img", attrs={
                    'src': 'img/{0}'.format(get_file(f(text))),
                }, styles={
                    'text-align': 'center',
                }).no_close()
                continue
            with Tag(content, "p") as p:
                    p.append(f(text))
            if lt == 'likert':
                with Tag(content, "p", styles={
                            'text-align': 'center',
                            'white-space': 'nowrap',
                        }) as p:
                    for v in range(5):
                        with Tag(p, "input", attrs={
                                    'name': lid,
                                    'type': 'radio',
                                    'value': v - 2,
                                    'checked': 'checked' if v == 2 else None,
                                }) as _:
                            pass
                        with Tag(p, "label", attrs={
                                    'for': lid,
                                }) as l:
                            l.append(v - 2)
            elif lt == 'text':
                pass
            else:
                raise ValueError("unknown line type: '{0}'".format(lt))

    if pt == 'plain':
        interpret_lines(content, page["lines"])
    elif pt == 'twocolumn':
        with Tag(content, "div", styles={
                    'float': 'left',
                    'width': '45vw',
                    'height': '80vh',
                    'overflow-y': 'auto',
                    'margin-right': '10px',
                }) as d:
            interpret_lines(d, page["left"])
        with Tag(content, "div", styles={
                    'float': 'right',
                    'width': '45vw',
                    'height': '80vh',
                    'overflow-y': 'auto',
                    'padding-left': '10px',
                    'border-left': 'black 1px solid',
                }) as d:
            interpret_lines(d, page["right"])
        with Tag(content, "div", styles={
                    'clear': 'both',
                }) as d:
            interpret_lines(d, page["bottom"])
    else:
        raise ValueError("unknown type: '{0}'".format(pt))
    con = page.get("continue", "next")
    with Tag(content, "p") as _:
        pass
    with Tag(content, "p", styles={
                'text-align': 'center',
                'white-space': 'nowrap',
            }) as p:
        last_page = False
        if con == 'end':
            last_page = True
        elif con == 'next':
            with Tag(p, "input", attrs={
                        'type': 'submit',
                        'name': '_nop_res',
                        'value': 'Next',
                    }) as _:
                pass
        elif con == 'choice':
            for ch in page["values"]:
                with Tag(p, "input", attrs={
                            'type': 'submit',
                            'name': 'res',
                            'value': ch,
                        }) as _:
                    pass
        else:
            raise ValueError("unknown continue: '{0}'".format(con))
    ask_unload = """window.onbeforeunload = (e) => {
            e.returnValue = "Data you have entered might not be saved. Continue closing?";
            return e.returnValue;
        }""" if not last_page else ""
    return content.finish(pid=pid, js=ask_unload, title=f(title)), pid, last_page


def read_spec(spec):
    with open(spec, 'r') as sin:
        sobj = json.load(sin)
    set_file_base(os.path.dirname(os.path.abspath(spec)))

    def flatten(layer, variables):
        for p in layer["pages"]:
            pt = p.get("type", "plain")
            if pt == 'each':
                var = p.get("vars", {})
                var.update(variables)

                def f(s):
                    return str(s).format(**var)

                name = f(p["name"])
                name_next = p.get("name_next", None)
                if name_next is not None:
                    name_next = f(name_next)
                name_prev = p.get("name_prev", None)
                if name_prev is not None:
                    name_prev = f(name_prev)
                for ix in range(int(f(p.get("from", 0))), int(f(p["to"]))):
                    cur_var = var.copy()
                    cur_var[name] = ix
                    if name_next is not None:
                        cur_var[name_next] = ix + 1
                    if name_prev is not None:
                        cur_var[name_prev] = ix - 1
                    for np in flatten(p, cur_var):
                        yield np
            else:
                p = p.copy()
                if "vars" not in p:
                    p["vars"] = {}
                p["vars"].update(variables)
                yield p

    title = sobj.get("title", "Survey")
    urlbase = sobj.get("urlbase", None)
    return list(flatten(sobj, {})), title, urlbase


if __name__ == '__main__':
    setup_restart()

    parser = argparse.ArgumentParser(description='Class Signature Server')
    parser.add_argument('-a', type=str, default="localhost", help="specifies the server address")
    parser.add_argument('-p', type=int, default=8080, help="specifies the server port")
    parser.add_argument('spec', type=str, help="JSON survey specification")
    parser.add_argument('output', type=str, help="output folder")
    args = parser.parse_args()

    addr = args.a
    port = args.p

    server, prefix = get_server(addr, port, read_spec(args.spec), args.output)
    msg("{0}", " ".join(sys.argv))
    msg("starting server at http://{0}:{1}{2}/", addr if addr else 'localhost', port, prefix)
    try:
        server.serve_forever()
    finally:
        msg("shutting down..")
        msg("{0}", " ".join(sys.argv))
        server.server_close()
