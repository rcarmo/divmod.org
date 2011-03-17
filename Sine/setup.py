from epsilon import setuphelper

from sine import version

setuphelper.autosetup(
    name="Sine",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/wiki/DivmodSine",
    license="MIT",
    platforms=["any"],
    description=
        """
        Divmod Sine is a standards-based voice-over-IP application server,
        built as an offering for the Mantissa application server platform.
        """,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Communications :: Conferencing",
        "Topic :: Communications :: Internet Phone",
        "Topic :: Communications :: Telephony",
        "Topic :: Internet",
        "Topic :: Multimedia :: Sound/Audio",
        ],
    )
