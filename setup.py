"""Setup module installation."""

import os

from setuptools import find_packages, setup


def load_requirements(path: str) -> list:
    with open(path, encoding="utf-8") as file:
        return [
            line.replace("==", ">=")
            for line in file.read().split("\n")
            if line and not line.startswith(("#", "-"))
        ]


if __name__ == "__main__":
    MODULE_NAME = "simplebot_connect4"
    DESC = "Connect Four game for Delta Chat (SimpleBot plugin)"
    URL = "https://github.com/simplebot-org/" + MODULE_NAME

    with open("README.rst") as fh:
        long_description = fh.read()

    setup(
        name=MODULE_NAME,
        setup_requires=["setuptools_scm"],
        use_scm_version={
            "root": ".",
            "relative_to": __file__,
            "tag_regex": r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
            "git_describe_command": "git describe --dirty --tags --long --match v*.*.*",
        },
        description=DESC,
        long_description=long_description,
        long_description_content_type="text/x-rst",
        author="The SimpleBot Contributors",
        author_email="adbenitez@nauta.cu",
        url=URL,
        keywords="simplebot plugin deltachat game",
        license="MPL",
        classifiers=[
            "Development Status :: 4 - Beta",
            "Environment :: Plugins",
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
            "Operating System :: OS Independent",
            "Topic :: Utilities",
        ],
        zip_safe=False,
        include_package_data=True,
        packages=find_packages(),
        install_requires=load_requirements("requirements.txt"),
        extras_require={"test": load_requirements("requirements-test.txt")},
        entry_points={
            "simplebot.plugins": "{0} = {0}".format(MODULE_NAME),
        },
    )
