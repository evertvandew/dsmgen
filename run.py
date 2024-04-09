#!/usr/bin/env python3

import http.server
import os
import os.path
import glob
import json
from http import HTTPStatus
from urllib.parse import urlparse, parse_qs
import subprocess

home = os.path.dirname(__file__)
os.chdir(os.path.dirname(__file__)+'/public')

class MyHandler(http.server.SimpleHTTPRequestHandler):
    doc_dir = home + '/diagrams'
    latest_file = home + '/diagrams/latest.txt'
    generate_script = home + '/generate_code'
    if not os.path.exists(doc_dir):
        os.mkdir(doc_dir)

    def do_GET(self):
        """ Handle requests for stored documents """
        path_parts = self.path.split('/')

        def handle_diagrams():
            # Check if this is a directory request or a specific file.
            if len(path_parts) == 2:
                # Directory request
                fnames = glob.glob("*.dia", root_dir=self.doc_dir)
                result = json.dumps(fnames).encode('utf8')
            elif len(path_parts) == 3:
                full_path = f"{self.doc_dir}/{path_parts[2]}"
                if not os.path.exists(full_path):
                    self.send_error(HTTPStatus.NOT_FOUND, "File not found")
                    return
                with open(full_path, 'rb') as infile:
                    result = infile.read()
            return result

        def handle_latest():
            """ Load the name of the latest diagram to be loaded """
            if os.path.exists(self.latest_file):
                with open(self.latest_file, 'rb') as lf:
                    return lf.read()
            return b''

        def handle_library():
            """ Generate and return the component library from its python specification """
            def generateJS(object):
                """ Serialize the object as Javascript """
                if isinstance(object, dict):
                    return "{" + ", ".join(f"{k}: {generateJS(v)}" for k, v in object.items()) + "}"
                elif isinstance(object, list):
                    return "[" + ", ".join(generateJS(v) for v in object) + "]"
                else:
                    raise f"Unsupported datatype {type(object)}"
            return f"""var library_dict = {generateJS(libraries)};""".encode('utf8')

        handler = {'diagrams': handle_diagrams,
                   'latest': handle_latest,
                   'library.js': handle_library
                   }.get(path_parts[1])
        if not handler:
            return super().do_GET()

        result = handler()
        if result:
            self.send_response(HTTPStatus.OK, "Available files follow")
            self.send_header('Content-Type', 'application/octet')
            self.send_header('Content-Length', len(result))
            self.end_headers()
            self.wfile.write(result)
            self.wfile.flush()

    def handle_save(self, url_parts):
        path_parts = url_parts.path.split('/')
        if len(path_parts) < 3:
            self.send_error(HTTPStatus.BAD_REQUEST, "Wrong path")
            return
        doc_name = path_parts[2]
        fname = f'{self.doc_dir}/{doc_name}'
        if not doc_name:
            # Generate a unique file name, to be returned later.
            count = 1
            while True:
                doc_name = f'document_{count}.dia'
                fname = f'{self.doc_dir}/{doc_name}'
                if not os.path.exists(fname):
                    break
                count += 1

        # Read the diagram data.
        length = self.headers.get('content-length')
        data = self.rfile.read(int(length))

        # Write the diagram data to the file.
        with open(fname, 'wb') as out:
            out.write(data)

        # Write the latest file
        with open(self.latest_file, 'wb') as out:
            out.write(doc_name.encode('utf8'))

        return doc_name.encode('utf8')

    def handle_rename(self, url_parts):
        parameters = parse_qs(url_parts.query)
        old_name = ''.join(parameters.get('orig', []))
        new_name = ''.join(parameters.get('new', []))

        if new_name[-4:] != ".dia":
            new_name += ".dia"

        if old_name and os.path.exists(self.doc_dir+'/'+old_name):
            # Move the file
            try:
                src, dst = [self.doc_dir+'/'+f for f in [old_name, new_name]]
                os.rename(src, dst)
            except os.error:
                self.send_error(HTTPStatus.BAD_REQUEST, "Wrong path")
                return
            # Write the latest file
            with open(self.latest_file, 'wb') as out:
                out.write(new_name.encode('utf8'))
        else:
            # The file doesn't yet exist: no action to be taken now
            pass

        return new_name.encode('utf8')

    def handle_generate(self, url_parts):
        # Read the diagram data.
        if 'application/x-www-form-urlencoded' in self.headers.get('Content-Type'):
            length = int(self.headers.get('content-length'))
            data = parse_qs(self.rfile.read(length), keep_blank_values=1)
        language = data.get(b'language')
        platform = data.get(b'platform')

        # Determine which diagram is to be generated
        with open(self.latest_file, 'rb') as input:
            diagram = input.read().decode('utf8')

        # The actual generation is done by a separate script.
        subprocess.run([self.generate_script, '-d', self.doc_dir + diagram, '-l', language, '-p', platform])

    def do_POST(self):
        """ Handle any POST request """
        if self.client_address[0] != '127.0.0.1':
            self.send_error(HTTPStatus.UNAUTHORIZED, "Not authorized")
            return
        url_parts = urlparse(self.path)
        if url_parts.netloc != '':
            self.send_error(HTTPStatus.BAD_REQUEST, "Wrong path")
            return
        path_parts = url_parts.path.split('/')

        handler = {'diagrams': self.handle_save,
                   'rename_diagram': self.handle_rename,
                   'generate_code': self.handle_generate}.get(path_parts[1])
        if not handler:
            self.send_error(HTTPStatus.BAD_REQUEST, "Wrong path")
            return

        result = handler(url_parts)
        if result:
            # Return a normal result
            # We return the document name, not the full file name
            self.send_response(HTTPStatus.OK, "Docname follows")
            self.send_header('Content-Type', 'application/octet')
            self.send_header('Content-Length', len(result))
            self.end_headers()
            self.wfile.write(result)
            self.wfile.flush()

if __name__ == '__main__':
    server_address = ('127.0.0.1', 8000)
    print("serving at", server_address)
    server_class = http.server.HTTPServer
    handler_class = MyHandler
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()
