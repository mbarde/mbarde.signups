# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

project = "mbarde.signups"
author = "Matthias Barde"
copyright = "Matthias Barde"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

# enable MyST extras: ::: fences for admonitions and auto-generated anchors
# for headings, so they can be linked as `page.md#some-heading`
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
myst_heading_anchors = 3

exclude_patterns = ["_build"]

html_theme = "plone_sphinx_theme"
html_title = "mbarde.signups"
html_theme_options = {
    "repository_url": "https://github.com/mbarde/mbarde.signups",
    "repository_branch": "main",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
}
