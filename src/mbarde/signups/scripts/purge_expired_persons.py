# -*- coding: utf-8 -*-
"""
Deletes UTPerson objects regarding `autoDeletePersonalDataAfterDays`
setting in UTSignupSheet.

Run it like:
venv/bin/zconsole run etc/zope.conf venv/bin/mbarde_signups_purge_expired_persons --no-dryrun --site-id Plone   # noqa: E501
"""

from mbarde.signups.utils import purgeExpiredPersonalData
from zope.component.hooks import setSite

import argparse
import sys
import transaction
import Zope2


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mbarde_signups_purge_expired_persons",
        description=__doc__,
    )
    parser.add_argument(
        "--dryrun",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="--dryrun (default) only report what would be deleted, --no-dryrun actually delete it",
    )
    parser.add_argument(
        "--site-id",
        required=True,
        help="Id of the Plone site to run against (as it appears in the site's URL).",
    )
    # zconsole/bin/instance run pass this script's own path (and possibly
    # other leading arguments, like the path to zope.conf) as part of
    # sys.argv - ignore anything we don't recognize instead of erroring
    args, _unknown = parser.parse_known_args(argv)

    # zconsole sets up the request and an elevated security manager for us,
    # but - unlike bin/instance run's -O<site-id> - doesn't traverse into a
    # particular Plone site, and plone.api needs an actual "current site"
    # to be set. Getting the Zope root via Zope2.app() (rather than relying
    # on the `app` name some invocation paths inject into __main__'s
    # globals) works regardless of how this script ends up being called.
    site = Zope2.app().unrestrictedTraverse(args.site_id)
    setSite(site)

    if args.dryrun:
        print("CHECK ONLY - pass --no-dryrun to actually delete anything")

    results = purgeExpiredPersonalData(dryRun=args.dryrun)

    if not results:
        print("Nothing to delete.")

    for result in results:
        verb = "would delete" if args.dryrun else "deleted"
        print(
            "[INFO] {verb} {count} person(s) from {sheet} / {day}".format(
                verb=verb, count=result["count"], sheet=result["sheet"], day=result["day"]
            )
        )

    if not args.dryrun:
        print("COMMIT")
        transaction.commit()


if __name__ == "__main__":
    sys.exit(main())
