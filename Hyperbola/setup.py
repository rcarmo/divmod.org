from epsilon import setuphelper

from hyperbola import version

setuphelper.autosetup(
    name="Hyperbola",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/wiki/DivmodHyperbola",
    license="MIT",
    platforms=["any"],
    description=
        """
        Divmod Hyperbola is a blogging platform developed as an Offering for
        Divmod Mantissa.
        """,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Communications",
        "Topic :: Internet"],
    )
