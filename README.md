# Set up for running or developing locally

Whether you're going to develop the app or just run it locally, you need to
follow these steps:

## ngrok

ngrok allows you to expose a localhost endpoint publicly
Create an account on ngrok
https://ngrok.com/

Then `brew install ngrok`

Follow the instructions on ngrok to add the auth token.

In a terminal tab run `ngrok http 8000`

Copy the Forwarding address, which will look like
`https://<random-id-here>.ngrok-free.app`

Note: this address will change every time you restart ngrok. You can get one static domain with a free account in the "Domains" tab - if you choose to do
that, remember to set your port to 8000 (ngrok's instructions default to 80).

## run the app

Start your virtual environment: `source .venv/bin/activate`
In another terminal tab, run the python server with `python3 ./main.py`

## slack app

Create [a slack app](https://api.slack.com/apps):

- Create New App -> From scratch -> choose a name and select the relevant workspace
- Select your new app, go to Features -> Slash Commands to create the command that will trigger this code:
  - Name the command
  - Assign your ngrok address to the Request URL
- In Settings -> Basic Information -> Install your app, choose the workspace to
  install it to

Save your changes

You should now be able to trigger your command in slack with `/name-you-chose`

And see the response "Hello, World! Here is a POST response. It worked!"
