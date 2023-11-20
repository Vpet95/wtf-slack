from http.server import BaseHTTPRequestHandler, HTTPServer
from Levenshtein import distance
import json
from urllib.parse import parse_qs, urlparse
import redis
r = redis.Redis()
r.ping()

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

r = redis.Redis(decode_responses=True)
# r.set('apple', 'the definition of apple')

# temp redis seeding:
for term in list_of_terms:
    r.set(term, f"the definition of {term}")
class handler(BaseHTTPRequestHandler):
    # example POST request handler - it just response with some text. We'll want to flesh this out
    # to parse out the request, figure out which term the user wants info for, query the db, and respond
    # OR use a nearest-distance algorithm and respond with suggestions
    # eventually: add functionality to populate the DB with new terms
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length).decode("utf-8")

        params = parse_qs(urlparse(body).path)

        # params['text'] has the user's query
        response = ""
        minimum_distance = -1
        user_entry = params["text"][0].lower()
        print(distance(user_entry, "term2"))
        if user_entry in list_of_terms:
            response = "The term you entered is in the list of terms."
            if r.get(user_entry) is not None:
                response += f" -> {r.get(user_entry)}"
        else:
            for term in list_of_terms:
                if (
                    distance(user_entry, term) < minimum_distance
                    and minimum_distance != -1
                ):
                    minimum_distance = distance(user_entry, term)
                    response = (
                        "The term you entered is not in the list of terms, the closest match is: "
                        + term
                        + " with a distance of: "
                        + str(minimum_distance)
                    )
                elif minimum_distance == -1:
                    minimum_distance = distance(user_entry, term)
                    response = (
                        "The term you entered is not in the list of terms, the closest match is: "
                        + term
                        + " with a distance of: "
                        + str(minimum_distance)
                    )

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
