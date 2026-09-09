# mbarde.signups

Plone-Addon to provide dynamic sign-up forms for events with single or multiple dates / timeslots available.

Originally inspired by https://github.com/collective/uwosh.timeslot (content-type prefixes still come from there):

> uwosh.timeslot offers a simple way to allow users of a Plone site to
> register for events (for example: training sessions or office hours).

## Features

- Define date based timeslots users can sign up to
- Logged in users can watch and manage their signups
- Timeslots can have capacities (waiting list and automatically moving up included)
- Customizable notification emails
- Dynamically extend signup form with EasyForm ([https://github.com/collective/collective.easyform](https://github.com/collective/collective.easyform))
- External mail validation via OTP

User states:

1. `unconfirmed`: Manager hast to confirm signup
2. `signedup`: User is signed up
3. `signedoff`: User is not signed up
4. `waiting`: User is on waiting list (moves up when another signup is cancelled)

## Dependecies

- [https://github.com/collective/collective.easyform](https://github.com/collective/collective.easyform)

## Installation

tbd.

## Usage

1. Create `UTSignupSheet`
2. Add `UTDay`
3. Add `UTTimeslot`

Optional: Create `EasyForm` and set as additional form in `UTSignupSheet` settings

**Important**: Ensure MailHost is configured properly (https://docs.plone.org/adapt-and-extend/config/mail.html).

## Contribute

- Issue Tracker: https://github.com/mbarde/unikold.timeslots/issues
- Source Code: https://github.com/mbarde/unikold.timeslots

## Development

### Setup

```
uv venv venv
source venv/bin/activate
uv pip install -e .
uv pip install -r requirements-dev.txt
```

### Test, lint & format

```
venv/bin/pytest
venv/bin/pytest -k name_of_a_test
venv/bin/black src/
venv/bin/flake8 src/
venv/bin/isort src/
```

### Run a local Plone instance

Create a Zope/Plone instance once (creates `instance/`, gitignored, with an
`admin` user):

```
venv/bin/mkwsgiinstance -d instance -u admin:admin
```

Start it:

```
venv/bin/runwsgi instance/etc/zope.ini
```

Then open http://localhost:8080 and use "Create a new Plone site" (log in as
`admin`), adding `mbarde.signups` (and `collective.easyform`) as add-ons
during site creation, or afterwards via _Site Setup > Add-ons_.

Set `debug-mode on` in `instance/etc/zope.conf` for template auto-reload
during development (Python changes still need a restart).

Signups and cancellations send notification emails, which fail locally
without a configured SMTP server (`ConnectionRefusedError`). With
`debug-mode on` and `Products.PrintingMailHost` installed (part of
`requirements-dev.txt`), outgoing mail is printed to the instance log
(`instance/var/log/event.log`) instead of actually being sent - no local
mail server needed.

### Update translations

```
source venv/bin/activate
uv pip install i18ndude
cd src/mbarde/signups/locales
./update.sh
```

Zope only ever loads compiled `.mo` catalogs at startup, never the `.po`
source files directly (and `.mo` files are gitignored, since they're a build
artifact). Add this to the `<environment>` section of
`instance/etc/zope.conf` so a fresh `.po` is automatically compiled to `.mo`
on every restart - otherwise translations silently keep showing the English
text no matter which language is negotiated:

```
<environment>
  zope_i18n_compile_mo_files true
</environment>
```

### VS Code setup

Plugins:

- `ms-python.black-formatter`: Python formatting
- `ms-python.flake8`: Python linting
- `ms-python.vscode-pylance`: Python language support
- `ms-python.isort`: Python imports sorting
- `esbenp.prettier-vscode`: .html/.pt/.md formatting
- `redhat.vscode-xml`: .xml formatting

Settings:

```json
{
  "[markdown]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "editor.formatOnSave": true,
  "files.associations": {
    "*.pt": "html",
    "*.zcml": "xml"
  },
  "editor.codeActionsOnSave": {
    "source.organizeImports": "always"
  }
}
```

## License

The project is licensed under the GPLv2, see [LICENSE.GPL](LICENSE.GPL).

## AI Usage

Parts of this addon were developed with assistance from Claude Code, Anthropic's agentic coding CLI, using the Claude Sonnet 5 model. The tool was used interactively under human direction and review.
