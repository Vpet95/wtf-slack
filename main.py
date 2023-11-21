from http.server import BaseHTTPRequestHandler, HTTPServer
from Levenshtein import distance
import json
from urllib.parse import parse_qs, urlparse
import requests
import redis

from seed_data.qp_glossary_seed_data import SEED_DATA

r = redis.Redis(decode_responses=True)
r.ping()

SLACK_OPEN_QUOTE = "“"
SLACK_CLOSE_QUOTE = "”"

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


# temp redis seeding:
for term in list_of_terms:
    r.set(term, f"the definition of {term}")

# QP glossary redis seeding:
for term, definition in SEED_DATA.items():
    r.set(term.lower(), definition)

print("Done seeding redis")
print(f"Redis seed example. r.get('AE'): {r.get('AE')}")

def parse_command_term_and_definition(text: str):
    # parse out the term and definition
    # the term might be multi-token and have quotes around it, so we need to handle that
    term_start_index = 1 if text[0] == SLACK_OPEN_QUOTE else 0
    term_end_char = SLACK_CLOSE_QUOTE if text[0] == SLACK_OPEN_QUOTE else (" " if " " in text else None)
    term_end_index = text.find(term_end_char) if term_end_char is not None else len(text)

    term = (text[term_start_index:term_end_index]).lower()
    definition = "" if len(term) == len(text) else (text[text.find(SLACK_CLOSE_QUOTE, 1) + 1:] if text[0] == SLACK_OPEN_QUOTE else text[text.find(' ') + 1:]).strip()

    return term, definition

def parse_command(command_name: str, text: str):
    if(command_name == '/wtf-delete'):
        term, _ = parse_command_term_and_definition(text)

        r.delete(term)

        return f"Deleted definition for '{term}'"
    if(command_name == '/wtf-update'):
        term, definition = parse_command_term_and_definition(text)

        if(r.get(term) is None):
            r.set(term, definition)
            return f"Term '{term}' not found. Added new definition for '{term}'"
        else:
            r.set(term, definition)
            return f"Updated definition for '{term}'"
    elif(command_name == '/wtf-add'):
        term, definition = parse_command_term_and_definition(text)
        print(f"Adding term: '{term}'")

        r.set(term, definition)

        return f"Added definition for '{term}'"
    else:
        # user is querying a term
        term, _ = parse_command_term_and_definition(text)
        definition = r.get(term)
        if definition is not None:
            return definition
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

def process_eli5(payload):
    print(payload)

    callback_id = payload['callback_id']

    # sanity check the callback id so we know it's our app talking
    if(callback_id != 'eli5_me'):
        return "Error: invalid callback_id"

    message = payload['message']['text']

    eli5_prompt = f"A Slack user wrote the following message: '{message}'. However, this message is a bit complex and full of domain-specific jargon. Please explain this message like I'm 5, making sure to unpack any bits of jargon in such a way that the message makes perfect sense and is fully transparent."

    # todo - submit prompt to some generative model
    
    response_url = payload['response_url']

    response = requests.post(response_url, json={ 'text': eli5_prompt, 'response_type': "in_channel" })
    print(f"Sent prompt to Slack; status code: {response.status_code}")

    return "success"

class handler(BaseHTTPRequestHandler):
    # example POST request handler - it just response with some text. We'll want to flesh this out
    # to parse out the request, figure out which term the user wants info for, query the db, and respond
    # OR use a nearest-distance algorithm and respond with suggestions
    # eventually: add functionality to populate the DB with new terms
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length).decode("utf-8")

        params = parse_qs(urlparse(body).path)
        #print(f"params: {params}")

        if('payload' in params):
            response = process_eli5(json.loads(params['payload'][0]))
            response_body = {
                'response_action': "ack"
            }
        else:
            response = "Error: missing term" if 'text' not in params else parse_command(params['command'][0], params['text'][0].lower())
            response_body = {
                "text": response,
                "response_type": "in_channel",
            }

        response_json = json.dumps(response_body)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

        self.wfile.write(bytes(response_json, "utf8"))


with HTTPServer(("", 8000), handler) as server:
    print("Server started on port 8000.")
    server.serve_forever()
