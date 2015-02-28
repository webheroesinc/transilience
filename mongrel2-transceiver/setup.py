from setuptools import setup

setup(
    name                        = "mongrel2-transceiver",
    packages                    = [
        "mongrel2_transceiver",
    ],
    package_dir                 = {
        "mongrel2_transceiver":		".",
        "mongrel2_transceiver/testing":	"./testing",
    },
    install_requires		= [
        'netifaces',
    ],
    version                     = "0.2.0",
    description                 = "Non-blocking Mongrel2 handler transceiver",
    author                      = "Matthew Brisebois",
    author_email                = "matthew@webheroes.ca",
    url                         = "https://github.com/webheroesinc/transilience",
    keywords                    = ["mongrel2", "zmq", "transceiver", "websocket", "http"],
    classifiers                 = [],
)
