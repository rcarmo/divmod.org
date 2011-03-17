
from epsilon import version, setuphelper

setuphelper.autosetup(
    name="Epsilon",
    version=version.short(),
    maintainer="Divmod, Inc.",
    maintainer_email="support@divmod.org",
    url="http://divmod.org/trac/wiki/DivmodEpsilon",
    license="MIT",
    platforms=["any"],
    description="A set of utility modules used by Divmod projects",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Topic :: Internet",
        "Topic :: Security",
        "Topic :: Utilities"],
    scripts=['bin/benchmark'])
