#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Project documentation build configuration file, created by
# sphinx-quickstart on Fri Mar 13 16:29:32 2015.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

import sphinx_rtd_theme

import git

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.mathjax',
    'sphinx.ext.todo',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinxcontrib.bibtex',
    'sphinx.ext.viewcode']

bibtex_bibfiles = [
    'source/bibtex/cite.bib',
    'source/bibtex/ref.bib',
    ]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = False
napoleon_use_rtype = False

todo_include_todos=True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
Affiliation = u'University of Trieste'
project = u'Lab Control'
copyright = u'2024, ' + Affiliation

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

# # Needs a VERSION file in the project top folder containing he full version, including alpha/beta/rc tags.
# version = open(os.path.join('..', 'VERSION')).read().strip()

# Alternatively we can use the git hash of the last repo commit to tag the doc version

# # This only works after the project is installed, i.e. will not work when building docs on readthedocs
# version = open(os.path.join('..', 'lclib', '_version.py')).readlines()[1]

# This requires an additional module: gitpython
repo    = git.Repo(search_parent_directories=True)
version = repo.git.rev_parse(repo.head, short=True)

release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = project+'doc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 
  project+'.tex',
  project+u' Documentation',
  Affiliation,'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index',project, 
    project+u' Documentation',
    [Affiliation,],
    1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 
  project, 
  project+u' Documentation',
  Affiliation, 
  project, 
  'Scientific Data Exchange'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#ztexinfo_no_detailmenu = False

# -- Options for Texinfo output -------------------------------------------
# http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_mock_imports
# autodoc_mock_imports = ['numpy', 
#                         'cython', 
#                         'h5py', 
#                         'napari', 
#                         'rpyc', 
#                         'zmq', 
#                         'signal', 
#                         'logging', 
#                         'select',
#                         'atexit', 
#                         'errno',] 

autodoc_mock_imports = ['wcwidth',
                        'snowballstemmer',
                        'pytz',
                        'PyOpenGL',
                        'pure-eval',
                        'ptyprocess',
                        'heapdict',
                        'appdirs',
                        'wrapt',
                        'urllib3',
                        'tzdata',
                        'typing-extensions',
                        'traitlets',
                        'tqdm',
                        'tornado',
                        'toolz',
                        'tomli-w',
                        'tabulate',
                        'sphinxcontrib-serializinghtml',
                        'sphinxcontrib-qthelp',
                        'sphinxcontrib-jsmath',
                        'sphinxcontrib-htmlhelp',
                        'sphinxcontrib-devhelp',
                        'sphinxcontrib-applehelp',
                        'six',
                        'shellingham',
                        'rpds-py',
                        'pyzmq',
                        'PyYAML',
                        'pyproject_hooks',
                        'pygments',
                        'psygnal',
                        'psutil',
                        'prompt-toolkit',
                        'plumbum',
                        'platformdirs',
                        'Pillow',
                        'pexpect',
                        'parso',
                        'packaging',
                        'numpy',
                        'networkx',
                        'nest-asyncio',
                        'napari-plugin-engine',
                        'mdurl',
                        'MarkupSafe',
                        'locket',
                        'lazy-loader',
                        'kiwisolver',
                        'in-n-out',
                        'imagesize',
                        'idna',
                        'hsluv',
                        'fsspec',
                        'freetype-py',
                        'executing',
                        'docutils',
                        'docstring-parser',
                        'decorator',
                        'debugpy',
                        'cython',
                        'cloudpickle',
                        'click',
                        'charset-normalizer',
                        'certifi',
                        'cachey',
                        'babel',
                        'attrs',
                        'appnope',
                        'annotated-types',
                        'alabaster',
                        'zmq',
                        'vispy',
                        'tifffile',
                        'scipy',
                        'rpyc',
                        'rpyc.core',
                        'rpyc.core.vinegar',
                        'requests',
                        'referencing',
                        'qtpy',
                        'python-dateutil',
                        'pydantic-core',
                        'pint',
                        'partd',
                        'matplotlib-inline',
                        'markdown-it-py',
                        'jupyter-core',
                        'Jinja2',
                        'jedi',
                        'imageio',
                        'h5py',
                        'comm',
                        'build',
                        'asttokens',
                        'superqt',
                        'stack-data',
                        'sphinx',
                        'scikit-image',
                        'rich',
                        'pydantic',
                        'pyconify',
                        'pooch',
                        'pandas',
                        'napari-svg',
                        'jupyter-client',
                        'jsonschema-specifications',
                        'dask',
                        'typer',
                        'pydantic-compat',
                        'numpydoc',
                        'jsonschema',
                        'IPython',
                        'npe2',
                        'magicgui',
                        'ipykernel',
                        'app-model',
                        'qtconsole',
                        'napari-console',
                        'napari',
                        'labcontrol-lib',
                        'numpy', 
                        'cython', 
                        'h5py', 
                        'napari', 
                        'napari_tools_menu',
                        'zmq', 
                        'signal', 
                        'logging', 
                        'select',
                        'atexit', 
                        'errno',
                        ]

# Mock a dictionary
from unittest.mock import Mock
from rpyc.core.vinegar import _generic_exceptions_cache

blah = Mock()
blah.__getitem__ = Mock()
blah.__getitem__.side_effect = _generic_exceptions_cache.__getitem__