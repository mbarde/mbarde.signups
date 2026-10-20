# -*- coding: utf-8 -*-
from pathlib import Path
from xml.etree import ElementTree

import mbarde.signups
import re
import unittest


def _parsePo(poFile):
    """msgid -> msgstr for single-line entries"""
    return dict(
        re.findall(
            r'^msgid "(.+)"\nmsgstr "(.*)"$',
            poFile.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )


class TranslationCatalogTest(unittest.TestCase):

    def test_no_fuzzy_entries(self):
        # msgfmt silently skips fuzzy entries, so their translations never
        # reach the compiled .mo catalog: the default email texts (see
        # _mailDefaultFactory) would then show up untranslated. i18ndude's
        # `sync` re-flags entries as fuzzy whenever their "#. Default:"
        # comment changes, which locales/update.sh strips again.
        localesDir = Path(mbarde.signups.__file__).parent / "locales"
        for poFile in localesDir.glob("*/LC_MESSAGES/*.po"):
            fuzzy = [
                line
                for line in poFile.read_text(encoding="utf-8").splitlines()
                if line == "#, fuzzy"
            ]
            self.assertEqual(fuzzy, [], "fuzzy entries in {0}".format(poFile))

    def test_workflow_titles_are_translated_in_plone_domain(self):
        # Plone translates workflow state and transition titles (toolbar
        # state menu, folder contents, ...) in the "plone" domain - not in
        # mbarde.signups - so they have to be in our plone.po catalogs
        packageDir = Path(mbarde.signups.__file__).parent
        definition = packageDir / "profiles/default/workflows/ut_person_workflow/definition.xml"
        root = ElementTree.parse(definition).getroot()
        titles = {state.get("title") for state in root.iter("state")}
        titles |= {transition.get("title") for transition in root.iter("transition")}
        titles |= {
            action.text.strip()
            for action in root.iter("action")
            if action.get("category") == "workflow"
        }

        translations = _parsePo(packageDir / "locales/de/LC_MESSAGES/plone.po")
        for title in sorted(titles):
            self.assertTrue(translations.get(title), "no German translation for " + title)

    def test_workflow_state_ids_are_translated_in_plone_domain(self):
        # folder_contents translates the raw review_state *id* (e.g.
        # "signedup") rather than the state title - so the ids need
        # entries too, in every language (otherwise even English would
        # show the bare id)
        packageDir = Path(mbarde.signups.__file__).parent
        definition = packageDir / "profiles/default/workflows/ut_person_workflow/definition.xml"
        root = ElementTree.parse(definition).getroot()
        stateIds = sorted(state.get("state_id") for state in root.iter("state"))

        for poFile in (packageDir / "locales").glob("*/LC_MESSAGES/plone.po"):
            translations = _parsePo(poFile)
            for stateId in stateIds:
                self.assertTrue(
                    translations.get(stateId),
                    "no translation for state id {0} in {1}".format(stateId, poFile),
                )
