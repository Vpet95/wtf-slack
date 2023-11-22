import argparse
import json
import os
import sys
import threading
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import redis
import requests
from Levenshtein import distance
from openai import OpenAI

from seed_data.qp_glossary_seed_data import SEED_DATA

r = redis.Redis(decode_responses=True)
r.ping()

SLACK_OPEN_QUOTE = "“"
SLACK_CLOSE_QUOTE = "”"

# Change prefix to whatever you're using locally to test. Leave as `wtf` for main app and demo.
COMMAND_PREFIX = "wtf"


class COMMANDS(Enum):
    QUERY = f"/{COMMAND_PREFIX}"
    ADD = f"/{COMMAND_PREFIX}-add"
    UPDATE = f"/{COMMAND_PREFIX}-update"
    DELETE = f"/{COMMAND_PREFIX}-delete"
    LIST = f"/{COMMAND_PREFIX}-list"
    HELP = f"/{COMMAND_PREFIX}-help"


term_arg = f"{SLACK_OPEN_QUOTE}[term]{SLACK_CLOSE_QUOTE}"
term_and_def_arg = f"{term_arg} [definition]"

command_info = {
    COMMANDS.QUERY: {"args": term_arg, "description": f"- lookup term in glossary."},
    COMMANDS.ADD: {
        "args": term_and_def_arg,
        "description": f"- add a term with definition to glossary.",
    },
    COMMANDS.UPDATE: {
        "args": term_and_def_arg,
        "description": f"- update existing term with a new definition.",
    },
    COMMANDS.DELETE: {
        "args": term_arg,
        "description": f"- delete a term from the glossary.",
    },
    COMMANDS.LIST: {
        "args": "",
        "description": f"- list all terms currently available in glossary.",
    },
    COMMANDS.HELP: {
        "args": "",
        "description": f"- list of available commands and other information.",
    },
}


def parse_command_term_and_definition(text: str):
    # parse out the term and definition
    # the term might be multi-token and have quotes around it, so we need to handle that
    term_start_index = 1 if text[0] == SLACK_OPEN_QUOTE else 0
    term_end_char = (
        SLACK_CLOSE_QUOTE
        if text[0] == SLACK_OPEN_QUOTE
        else (" " if " " in text else None)
    )
    term_end_index = (
        text.find(term_end_char) if term_end_char is not None else len(text)
    )

    term = (text[term_start_index:term_end_index]).lower()
    definition = (
        ""
        if len(term) == len(text)
        else (
            text[text.find(SLACK_CLOSE_QUOTE, 1) + 1 :]
            if text[0] == SLACK_OPEN_QUOTE
            else text[text.find(" ") + 1 :]
        ).strip()
    )

    return term, definition


def parse_command(command_name: str, text: str):
    if command_name == COMMANDS.DELETE.value:
        term, _ = parse_command_term_and_definition(text)

        r.delete(term)

        return f"Deleted definition for '{term}'"
    if command_name == COMMANDS.UPDATE.value:
        term, definition = parse_command_term_and_definition(text)

        if r.get(term) is None:
            r.set(term, definition)
            return f"Term '{term}' not found. Added new definition for '{term}'"
        else:
            r.set(term, definition)
            return f"Updated definition for '{term}'"
    elif command_name == COMMANDS.ADD.value:
        term, definition = parse_command_term_and_definition(text)
        print(f"Adding term: '{term}'")

        r.set(term, definition)

        return f"Added definition for '{term}'"
    elif command_name == COMMANDS.LIST.value:
        terms = r.keys()
        return f"Available terms are: \n{', '.join(terms)}"
    elif command_name == COMMANDS.HELP.value:
        return (
            "\n".join(
                f"`{command.value} {command_info.get(command)['args']}` {command_info.get(command)['description']}"
                for command in COMMANDS
            )
            + "\n\nA lot of the terms in the glossary were gathered from <https://www.gainsight.com/guides/the-essential-guide-to-recurring-revenue/|this really helpful site>."
        )
    else:
        # user is querying a term
        term, _ = parse_command_term_and_definition(text)
        definition = r.get(term)
        if definition is not None:
            return definition
        else:
            minimum_distance = -1
            likely_match = ""

            for term in r.keys():
                current_distance = distance(text, term)
                if minimum_distance == -1 or current_distance < minimum_distance:
                    minimum_distance = current_distance
                    likely_match = term

            add_definition_instructions = f'add a definition for it with `{COMMANDS.ADD.value} ["][term]["] [definition]`'
            return (
                f"Term '{text}' not found. Did you mean '{likely_match}'? Alternatively, {add_definition_instructions}"
                if minimum_distance <= round(len(term) / 2)
                else f"Term '{text}' not found. You can {add_definition_instructions}."
            )


def process_eli5(payload):
    print(f">>>> process_eli5() payload: {payload}")

    callback_id = payload["callback_id"]
    is_private = callback_id == "eli5_me_privately"

    try:
        if client:
            # sanity check the callback id so we know it's our app talking
            if callback_id != "eli5_me" and callback_id != "eli5_me_privately":
                return "Error: invalid callback_id"

            message = payload["message"]["text"]

            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Can you please explain the following message from Slack in simple terms for someone who doesn't have any background knowledge? I don't want just a summary, but a detailed explanation. Please clarify any technical terms, acronyms, or jargon used. The message says '{message}'",
                    }
                ],
            )
            reply_text = completion.choices[0].message.content
        else:
            reply_text = "Sorry, this feature is disabled at the moment."

    except Exception as e:
        print(f">>>> process_eli5 error: {e}")
        reply_text = "Sorry, something went wrong. Please try again or contact your friendly bot-keeper for help."

    print(f">>>> process_eli5 reply_text: {reply_text}")
    response_url = payload["response_url"]

    link_to_original_message = f"https://{payload['team']['domain']}.slack.com/archives/{payload['channel']['id']}/p{str(payload['message_ts']).replace('.', '')}"
    response = requests.post(
        response_url,
        json={
            "text": reply_text,
            **({} if is_private else {"response_type": "in_channel"}),
            **(
                {}
                if is_private
                else {
                    "attachments": [
                        {"text": f"<{link_to_original_message}|Original message>"}
                    ]
                }
            ),
        },
    )
    print(
        f">>>> process_eli5 Sent prompt to Slack; status code: {response.status_code}"
    )

    return "success"


def processing_message(response_url: str):
    response = requests.post(
        response_url,
        json={
            "text": "Ok, I'm working on deciphering that message. This may take several seconds, sit tight!"
        },
    )
    print(f"processing_message status code: {response.status_code}")


class handler(BaseHTTPRequestHandler):
    def acknowledge(self):
        ack_response = {"response_action": "ack"}
        ack_response_json = json.dumps(ack_response)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(ack_response_json, "utf8"))

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length).decode("utf-8")

        params = parse_qs(urlparse(body).path)
        # print(f"params: {params}")

        if "payload" in params:
            payload = json.loads(params["payload"][0])

            # acknowledge receipt of slack action
            self.acknowledge()

            # the openai request can take a bit of time, let the user know we're working on it
            processing_message(payload["response_url"])

            # process request
            threading.Thread(target=process_eli5, args=(payload,)).start()
            # response = process_eli5(json.loads(params['payload'][0]))
            # response_body = {
            #     'response_action': "ack"
            # }
        else:
            command = params["command"][0]
            if command in [COMMANDS.HELP.value, COMMANDS.LIST.value]:
                response = parse_command(command, "")
            else:
                response = (
                    "Error: missing term"
                    if "text" not in params
                    else parse_command(command, params["text"][0].lower())
                )
            response_body = {
                "text": response,
                "response_type": "in_channel",
            }

            response_json = json.dumps(response_body)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            self.wfile.write(bytes(response_json, "utf8"))


if __name__ == "__main__":
    with HTTPServer(("", 8000), handler) as server:
        print("Server started on port 8000.")
        parser = argparse.ArgumentParser(
            prog="Slack Slash Command Glossary and ELI5 Bot",
            description="Returns definitions for common QP terms (allowing updates and edits), and provides explanations of input text on demand.",
            epilog="made with <3 by Maeve and Vuk and Rinat and Kborg",
        )
        parser.add_argument(
            "--seed",
            required=False,
            type=bool,
            default=False,
            help="Whether to seed the database with sample data. Run without this flag to preserve updates to seed data definitions from previous runs. Defaults to False.",
        )
        parser.add_argument(
            "--no-ai",
            required=False,
            type=bool,
            default=False,
            help="Allow the app to run without the open ai key, also turning off the ai commands. Defaults to False.",
        )
        args = parser.parse_args()
        if args.seed:
            print("Seeding database")
            for term, definition in SEED_DATA.items():
                r.set(term.lower(), definition)

            print("Done seeding redis")
            print(f"Redis seed example. r.get('AE'): {r.get('AE')}")
        if args.no_ai == True:
            client = None
            print("Running without AI")
        else:
            # the openai library automatically reads this in, we're just sanity checking here so we can terminate the server
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

            if OPENAI_API_KEY is None:
                print("Error: missing OPENAI_API_KEY environment variable")
                sys.exit(1)
            client = OpenAI()

        server.serve_forever()
