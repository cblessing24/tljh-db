import os
import json
import configparser

import pymysql
from xkcdpass import xkcd_password as xp

from tljh.hooks import hookimpl


@hookimpl
def tljh_new_user_create(username):
    config = configparser.ConfigParser()
    config.read("/srv/tljh-db.ini")

    password = generate_password(config)
    create_user(config, username, password)
    generate_datajoint_config(config, username, password)


def generate_password(config):
    wordfile = xp.locate_wordfile()
    words = xp.generate_wordlist(wordfile)
    return xp.generate_xkcdpassword(
        words, numwords=config["DEFAULT"].get("NumWords", 6), delimiter=config["DEFAULT"].get("Delimiter", "-")
    )


def create_user(config, username, password):
    connection = pymysql.connect(
        host=config["DEFAULT"]["Host"], user=config["DEFAULT"]["User"], password=config["DEFAULT"]["Password"]
    )
    try:
        with connection.cursor() as cursor:
            sql_statements = [
                fr"CREATE USER '{username}'@'%' IDENTIFIED BY '{password}'",
                fr"GRANT ALL PRIVILEGES ON `{username}\_%`.* TO '{username}'@'%'",
            ]
            for sql in sql_statements:
                cursor.execute(sql)
            connection.commit()
    finally:
        connection.close()


def generate_datajoint_config(config, username, password):
    dj_config_data = {
        "database.host": config["DEFAULT"]["Host"],
        "database.password": password,
        "database.user": username,
        "database.port": config["DEFAULT"].get("Port", 3306),
        "database.reconnect": True,
        "connection.init_function": None,
        "connection.charset": "",
        "loglevel": "INFO",
        "safemode": True,
        "fetch_format": "array",
        "display.limit": 12,
        "display.width": 14,
        "display.show_tuple_count": True,
        "database.use_tls": None,
        "enable_python_native_blobs": False,
    }
    with open(os.path.join("/home", "jupyter-" + username, "dj_local_conf.json"), "w") as dj_config_file:
        json.dump(dj_config_data, dj_config_file, indent=True)
