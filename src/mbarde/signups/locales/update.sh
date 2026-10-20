#!/bin/bash
# i18ndude should be available in current $PATH (eg by running
# ``export PATH=$PATH:$BUILDOUT_DIR/bin`` when i18ndude is located in your buildout's bin directory)
#
# For every language you want to translate into you need a
# locales/[language]/LC_MESSAGES/mbarde.signups.po
# (e.g. locales/de/LC_MESSAGES/mbarde.signups.po)

domain=mbarde.signups

i18ndude rebuild-pot --pot $domain.pot --create $domain ../
i18ndude sync --pot $domain.pot */LC_MESSAGES/$domain.po

# `sync` flags entries whose "#. Default:" comment changed as fuzzy, and
# msgfmt silently skips fuzzy entries - so their translations would never
# make it into the compiled .mo (e.g. the default email texts would show up
# untranslated). This project doesn't use fuzzy translations on purpose, so
# drop the flag.
sed -i '/^#, fuzzy$/d' */LC_MESSAGES/$domain.po

# Workflow state/transition titles are translated by Plone in the "plone"
# domain (toolbar state menu, folder contents, ...), not in our own domain.
# Ship them in a separate plone.po, merged by Zope with Plone's own catalog.
i18ndude rebuild-pot --pot plone.pot --create plone ../profiles/default/workflows
for lang in */; do
    lang=${lang%/}
    [ -f $lang/LC_MESSAGES/plone.po ] || touch $lang/LC_MESSAGES/plone.po
done
i18ndude sync --pot plone.pot */LC_MESSAGES/plone.po
sed -i '/^#, fuzzy$/d' */LC_MESSAGES/plone.po
