from setuptools import setup

setup(
    name                        = "mongrel2-transceiver",
    packages                    = [
        "mongrel2_transceiver",
    ],
    package_dir                 = {
        "mongrel2_transceiver":		".",
    },
    install_requires		= [
        'netifaces',
    ],
    version                     = "0.3.0",
    include_package_data        = True,
    author                      = "Matthew Brisebois",
    author_email                = "matthew@webheroes.ca",
    url                         = "https://github.com/webheroesinc/transilience",
    license                     = "Dual License; GPLv3 and Proprietary",
    description                 = "Non-blocking Mongrel2 handler transceiver",
    long_description		= """Mongrel2 Transceiver was built to solve 3 major hassles that
come with trying to handle ZMQ and WebSockets.

1. Handling WebSockets properly
2. Dynamically adding more connections to a running handlers
3. Reliably destroying ZMQ Contexts

Transceiver solves all these issues with an intuitive and simplistic syntax.

WARNING: Mongrel2 Transceiver was primarily designed to work with Docker containers.  Therefore the
default options for all the classes are not expecting to have issues binding to the default ports.
It is your job to configure custom ports if you will be running in a single network environment.
Every class has options for overriding the default ports and have been tested in a single network
environment.  """,
    keywords                    = ["mongrel2", "zmq", "transceiver", "websocket", "http"],
    classifiers                 = [
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 2.7",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
    ],
)
