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


__version__ = "0.0.2"


def get_server(addr, port, full_spec, output):
    spec, title = full_spec
    server = create_server((addr, port))

    prefix = '/' + os.path.basename(os.path.normpath(server.base_path))

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
        if "post" in args:
            with token_lock:
                tobj = token_obj(token)
                pobj = args["post"]
                pid = pobj["_pid"]
                for (k, v) in pobj.items():
                    if k == "_pid":
                        continue
                    tobj["{0}:{1}".format(pid, k)] = v
                write_token(token, tobj)
        pix = int(args["query"]["pix"])
        url = "?pix={0}&token={1}".format(pix + 1, token)
        res, last_page = create_page(spec, pix, url, token, title)
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
    for (pix, s) in enumerate(spec):
        create_page(spec, pix, "NOPE", "ANON", "DRY")


def create_page(spec, pix, url, token, title):
    p = spec[pix]
    pt = p.get("type", "plain")
    var = p["vars"].copy()
    var["_token"] = token

    def f(s):
        return str(s).format(**var)

    pid = f(p.get("pid", "p{0}".format(pix)))
    content = ""
    if pt != 'plain':
        raise ValueError("unknown type: '{0}'".format(pt))
    for line in p["lines"]:
        if isinstance(line, basestring):
            content += "<p>{0}</p>".format(f(line))
            continue
        lt, text, lid = line
        if lt == 'img':
            content += """<img src="img/{0}" style="text-align: center;">""".format(
                                            get_file(f(text)))
            continue
        content += "<p>{0}</p>".format(f(text))
        if lt == 'likert':
            content += "<p style=\"text-align: center; white-space: nowrap;\">"
            for v in range(5):
                content += """
                <input name="{0}" type="radio" value="{1}"{2}></input>
                <label for="{0}">{1}</label>""".format(
                        lid,
                        v - 2,
                        " checked=\"checked\"" if v == 2 else ""
                    )
            content += "</p>"
        elif lt == 'text':
            pass
        else:
            raise ValueError("unknown line type: '{0}'".format(lt))
    con = p.get("continue", "next")
    content += """<p></p><p style="text-align: center; white-space: nowrap;">"""
    last_page = False
    if con == 'end':
        content += ""
        last_page = True
    elif con == 'next':
        content += """<input type="submit" name="_res" value="Next"></input>""".format(url)
        pass
    elif con == 'choice':
        for ch in p["values"]:
            content += """<input type="submit" name="_res" value="{0}"></input>""".format(ch)
    else:
        raise ValueError("unknown continue: '{0}'".format(con))
    content += "</p>"
    ask_unload = """window.onbeforeunload = (e) => {
            e.returnValue = "Data you have entered might not be saved. Continue closing?";
            return e.returnValue;
        }""" if not last_page else ""
    return """<!DOCTYPE html>
    <head>
        <title>{4}</title>
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
                <form id="main_form" action="{0}" method="post">
                {1}
                <input type="hidden" value="{2}" name="_pid"></input>
                </form>
            </div>
            <div style="flex-grow: 0.5; flex-shrink: 1;">
            </div>
        </div>
        <script>
            {3}
            document.getElementById("main_form").onsubmit = () => {{
                window.onbeforeunload = null;
            }};
        </script>
    </body>
    """.format(url, content, pid, ask_unload, f(title)), last_page


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
                name = p["name"].format(**var)
                for ix in range(int(str(p.get("from", 0)).format(**var)), int(p["to"].format(**var))):
                    cur_var = var.copy()
                    cur_var[name] = ix
                    for np in flatten(p, cur_var):
                        yield np
            else:
                p = p.copy()
                if "vars" not in p:
                    p["vars"] = {}
                p["vars"].update(variables)
                yield p

    title = sobj.get("title", "Survey")
    return list(flatten(sobj, {})), title


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
