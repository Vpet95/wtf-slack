from http.server import BaseHTTPRequestHandler, HTTPServer
from Levenshtein import distance
import json
from urllib.parse import parse_qs, urlparse

list_of_terms = [
    "apple",
    "banana",
    "cherry",
    "date",
    "elderberry",
    "fig",
    "grape",
    "honeydew",
    "kiwi",
    "lemon",
    "mango",
    "nectarine",
    "orange",
    "papaya",
    "quince",
    "raspberry",
    "strawberry",
    "tangerine",
    "ugli fruit",
    "watermelon",
]

def parse_command(command_name: str, text: str):
    if(command_name == '/wtf-add'):
        # todo - implement logic for adding terms 
        # syntax looks like /wtf-add ["] term ["] definition 
        # where term can be surrounded by double-quotes if it's a multi-word term. 
        # Everything after it is considered the definition.

        pass 
    else:
        # user is querying a term        
        if text in list_of_terms:
            return f"<Definition for {text} here>"
        else:
            minimum_distance = -1
            likely_match = ""

            for term in list_of_terms:
                current_distance = distance(text, term)
                if (
                    minimum_distance == -1 or current_distance < minimum_distance
                ):
                    minimum_distance = current_distance
                    likely_match = term
            
            return f"Term '{text}' not found. Did you mean '{likely_match}'? Alternatively, add a definition for it with `/wtf-add [\"]<term>[\"] <definition>`"

class handler(BaseHTTPRequestHandler):
    # example POST request handler - it just response with some text. We'll want to flesh this out
    # to parse out the request, figure out which term the user wants info for, query the db, and respond
    # OR use a nearest-distance algorithm and respond with suggestions
    # eventually: add functionality to populate the DB with new terms
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length).decode("utf-8")

        params = parse_qs(urlparse(body).path)

        response = parse_command(params['command'], params['text'][0])

        response_data = {
            "text": response,
            "response_type": "in_channel",
        }
        response_json = json.dumps(response_data)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        self.wfile.write(bytes(response_json, "utf8"))


with HTTPServer(("", 8000), handler) as server:
    print("Server started on port 8000.")
    server.serve_forever()
