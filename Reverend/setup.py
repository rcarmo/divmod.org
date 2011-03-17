# This module is part of the Reverend project and is Copyright 2003 Amir
# Bakhtiar (amir@divmod.org). This is free software; you can redistribute
# it and/or modify it under the terms of version 2.1 of the GNU Lesser
# General Public License as published by the Free Software Foundation.

from distutils.core import setup

setup(name="Reverend",
      version="0.4",
      description="Divmod Reverend - a simple Bayesian classifier",
      author="Amir Bakhtiar",
      author_email="amir hat divmod point org",
      url="http://www.divmod.org/",
      packages=['reverend', 'reverend.ui', 'reverend.guessers'],
      classifiers=[
            "Development Status :: 7 - Inactive",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
            "Natural Language :: English",
            "Programming Language :: Python",
            "Topic :: Communications :: Email :: Filters",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "Topic :: Text Processing",
            ])
