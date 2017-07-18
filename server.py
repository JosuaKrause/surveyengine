#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division

import os
import sys
import json
import math
import argparse
import threading

from quick_server import create_server, msg, setup_restart, Response, PreventDefaultResponse

def get_server(addr, port, spec, output):
    server = create_server((addr, port))

    prefix = '/' + os.path.basename(os.path.normpath(server.base_path))

    server.link_empty_favicon_fallback()

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

    @server.text_get(prefix + '/', 0)
    def text_index(req, args):
        return post_index(req, args)

    @server.text_post(prefix + '/', 0)
    def post_index(req, args):
        if "token" not in args["query"]:
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
        res, last_page = create_page(spec, pix, url)
        if last_page:
            msg("{0} finished!", token)
        return Response(res, ctype="text/html")

    return server, prefix

def create_page(spec, pix, url):
    p = spec[pix]
    pt = p["type"]
    var = p["vars"]
    pid = p.get("pid", "p{0}".format(pix)).format(**var)
    if pt == 'text':
        content = "<p>{0}</p>".format(p["text"].format(**var))
    elif pt == 'img':
        content = "<img src={0}>".format(p["file"].format(**var))
    elif pt == 'input':
        content = ""
        for line in p["lines"]:
            lid, text, lt = line
            content += "<p>{0}</p><p>".format(text.format(**var))
            if lt == 'likert':
                for v in range(5):
                    content += """
                    <input name="{0}" type="radio" value="{1}"{2}></input>
                    <label for="{0}">{1}</label>""".format(
                            lid,
                            v - 2,
                            " checked=\"checked\"" if v == 2 else ""
                        )
            else:
                raise ValueError("unknown line type: '{0}'".format(lt))
            content += "</p>"
    else:
        raise ValueError("unknown type: '{0}'".format(pt))
    con = p["continue"]
    content += "<p></p><p>"
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
    return """<!DOCTYPE html>
    <body>
        <form action="{0}" method="post">
        {1}
        <input type="hidden" value="{2}" name="_pid"></input>
        </form>
    </body>
    """.format(url, content, pid), last_page

def read_spec(spec):
    with open(spec, 'r') as sin:
        sobj = json.load(sin)

    def flatten(layer, variables):
        for p in layer["pages"]:
            pt = p["type"]
            if pt == 'each':
                name = p["name"]
                for ix in range(p.get("from", 0), p["to"]):
                    var = variables.copy()
                    var[name] = ix
                    for np in flatten(p, var):
                        yield np
            else:
                p = p.copy()
                if "vars" not in p:
                    p["vars"] = {}
                p["vars"].update(variables)
                yield p

    return list(flatten(sobj, {}))

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
