# Automatic deletion of personal data

Editors can set _Automatically delete personal data after (days)_ for each
signup sheet (see {doc}`../editors/data-privacy`). The deletion is not done
by Plone itself: to have any effect, a cron job needs to run the script
`mbarde_signups_purge_expired_persons` regularly.

The script is installed together with the package (see `[project.scripts]`
in `pyproject.toml`) and has to be run via `zconsole`, so it can access the
database:

```shell
cd /path/to/instance && venv/bin/zconsole run etc/zope.conf venv/bin/mbarde_signups_purge_expired_persons --no-dryrun --site-id Plone
```

Options:

`--site-id`
: Id of the Plone site to run against (as it appears in the site's URL).
  Required.

`--dryrun` / `--no-dryrun`
: By default, the script only reports what would be deleted. Pass
  `--no-dryrun` to actually delete it.

Run it without `--no-dryrun` first to check what would be deleted.

## Cron job

For example, to run the script every night at 3 am:

```text
0 3 * * * cd /path/to/instance && venv/bin/zconsole run etc/zope.conf venv/bin/mbarde_signups_purge_expired_persons --no-dryrun --site-id Plone
```
