from epsilon import setuphelper

from xquotient import version

setuphelper.autosetup(
    name="Quotient",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/wiki/DivmodQuotient",
    license="MIT",
    platforms=["any"],
    description=
        """
        Divmod Quotient is a messaging platform developed as an Offering for
        Divmod Mantissa.
        """,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Communications :: Email",
        "Topic :: Communications :: Email :: Address Book",
        "Topic :: Communications :: Email :: Email Clients (MUA)",
        "Topic :: Communications :: Email :: Filters",
        "Topic :: Communications :: Email :: Post-Office :: POP3",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        ],
    )
