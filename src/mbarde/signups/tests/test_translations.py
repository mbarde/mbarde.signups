# -*- coding: utf-8 -*-
from pathlib import Path

import mbarde.signups
import unittest


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
