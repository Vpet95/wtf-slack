from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class handler(BaseHTTPRequestHandler):
    # example POST request handler - it just response with some text. We'll want to flesh this out 
    # to parse out the request, figure out which term the user wants info for, query the db, and respond
    # OR use a nearest-distance algorithm and respond with suggestions 
    # eventually: add functionality to populate the DB with new terms 
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type','application/json')
        self.end_headers()

        response_data = { 'text': "Hello, World! Here is a POST response. It worked!", "response_type": "in_channel"}
        response_json = json.dumps(response_data)

        self.wfile.write(bytes(response_json, "utf8"))

with HTTPServer(('', 8000), handler) as server:
    print("Server started on port 8000.")
    server.serve_forever()