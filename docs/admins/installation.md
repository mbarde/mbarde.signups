# Installation

## Requirements

- Plone 6
- Python 3.12 or newer
- [collective.easyform](https://github.com/collective/collective.easyform)
  (installed automatically as a dependency)

## Install the package

```shell
uv pip install mbarde.signups
```

(or `pip install mbarde.signups`, or add it to the requirements of your
deployment)

Restart the instance afterwards.

## Activate the add-on

Activate `mbarde.signups` in _Site Setup > Add-ons_, or select it when
creating a new Plone site.

On installation, the add-on

- adds the content types `UTSignupSheet`, `UTDay`, `UTTimeslot` and
  `UTPerson` (see {doc}`../editors/structure`),
- shows signup sheets in the navigation, but hides days, timeslots and
  persons from navigation and search,
- adds the {doc}`control panel <setup>` _mbarde.signups Settings_.

Next, continue with the {doc}`setup`.
