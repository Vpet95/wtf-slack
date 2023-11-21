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

Note: this address will change every time you restart ngrok, and you'll need
to keep updating your slash command's destination url in slack.
You can get one static domain with a free account in the "Domains" tab - if you choose to do
that, remember to set your port to 8000 (ngrok's instructions default to 80).

## redis

Install redis-stack:
`brew tap redis-stack/redis-stack`
then
`brew install redis-stack`

Follow [the instructions here](https://redis.io/docs/install/install-stack/mac-os/)
to check and update your `$PATH` with the correct redis-stack-server version

In another terminal tab, start the redis stack server: `redis-stack-server`

## ELi5 Setup

For the ELI5 dropdown action, you'll need to:

- Set up the dropdown actions in slack, once you've made your app (see [below for more info](#set-up-slack-message-dropdown-options))
- [make an OpenAI account](https://auth0.openai.com/u/signup/identifier?state=hKFo2SBuWlR1Zll4ZnluNUF2WXN3ZjhpSjVPcDREOS16d0gxT6Fur3VuaXZlcnNhbC1sb2dpbqN0aWTZIHQwRjFKUkwxS2hpMlhBd1dTa0QwUzJkbTByb08zd0RFo2NpZNkgRFJpdnNubTJNdTQyVDNLT3BxZHR3QjNOWXZpSFl6d0Q).
- Then, [add an API key](https://platform.openai.com/api-keys)
- Store the API key in an environment variable in your `~/.zprofile` file like so:
  ```
  export OPENAI_API_KEY="<your key here>"
  ```
  Note: the environment variable name here matters and needs to be exact - this is what the open AI library looks for under the hood.

New OpenAI accounts receive $5 of free credit, and each GPT request is fairly inexpensive so this should be sufficient for the hackathon.

If you want to bypass this functionality and run without an OPENAI_API_KEY set,
you can pass a flag when running the app (see ["run the app" section, below](#run-the-app))

## run the app

In another terminal tab:
Install python dependencies with `pip install -r requirements.txt`

Then run the python server:
The first time you run, you may want to seed the db with common QP terms and
definitions. Use: `python3 ./main.py --seed=true`

To run without seeding, use `python3 ./main.py`

To allow the app to run without setting an `OPENAI_API_KEY`, disabling the
eli5 command, use: `python3 ./main.py --no-ai=true`

Call the app's help for more information `python3 ./main.py --help`

# hot reloading

If you want your server to hot reload when you make changes to `main.py`, run it with [jurigged](https://github.com/breuleux/jurigged) instead.

First, `pip install jurigged`.
Then run the app `python3 -m jurigged -v main.py` (do this instead of the command in the previous section).

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

### set up slack message dropdown options

To enable the ELI5 features, you need to do additional setup.

Go to the [settings page for your slack apps](https://api.slack.com/apps) and
select your app:

In Features > Interactivity & Shortcuts, you need to:

- Turn on "Interactivity"
- Add your ngrok url to "Request URL"
- "Create New Shortcut" twice (In both cases, the Name can be whatever you want, but the callback must match
  the strings below exactly):
  - Name: ELI5, Location: Messages, Callback ID: eli5_me
  - Name: ELI5, Location: Messages, Callback ID: eli5_me_privately

You should now be able to click on the 3 dot menu for any message, and select
your shortcut. If you don't see yours, select "More Message Shortcuts" and search by name.
