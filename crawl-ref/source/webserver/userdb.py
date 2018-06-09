import crypt
import sqlite3
import re
import os.path
import logging
import random
import smtplib

from config import (max_passwd_length, nick_regex, password_db,
                    crypt_algorithm, crypt_salt_length)

def user_passwd_match(username, passwd): # Returns the correctly cased username.
    try:
        passwd = passwd[0:max_passwd_length]
    except:
        return None

    try:
        conn = sqlite3.connect(password_db)
        c = conn.cursor()
        c.execute("select username,password from dglusers where username=? collate nocase",
                  (username,))
        result = c.fetchone()

        if result is None:
            return None
        elif crypt.crypt(passwd, result[1]) == result[1]:
            return result[0]
    finally:
        if c: c.close()
        if conn: conn.close()

def ensure_user_db_exists():
    if os.path.exists(password_db): return
    logging.warn("User database didn't exist; creating it now.")
    c = None
    conn = None
    try:
        conn = sqlite3.connect(password_db)
        c = conn.cursor()
        schema = ("CREATE TABLE dglusers (id integer primary key," +
                  " username text, email text, env text," +
                  " password text, flags integer);")
        c.execute(schema)
        conn.commit()
    finally:
        if c: c.close()
        if conn: conn.close()

saltchars = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def make_salt(saltlen):
    return ''.join(random.choice(saltchars) for x in xrange(0,saltlen))

def register_user(username, passwd, email): # Returns an error message or None
    if passwd == "": return "The password can't be empty!"
    passwd = passwd[0:max_passwd_length]
    username = username.strip()
    if not re.match(nick_regex, username): return "Invalid username!"

    if crypt_algorithm == "broken":
        salt = passwd
    elif crypt_algorithm:
        salt = "$%s$%s$" % (crypt_algorithm, make_salt(crypt_salt_length))
    else:
        salt = make_salt(2)

    crypted_pw = crypt.crypt(passwd, salt)

    try:
        conn = sqlite3.connect(password_db)
        c = conn.cursor()
        c.execute("select username from dglusers where username=? collate nocase",
                  (username,))
        result = c.fetchone()

        if result: return "User already exists!"

        c.execute("insert into dglusers(username, email, password, flags, env) values (?,?,?,0,'')",
                  (username, email, crypted_pw))

        conn.commit()

        return None
    finally:
        if c: c.close()
        if conn: conn.close()

def send_forgot_password(email): # Returns a tuple where item 1 is a truthy value when an email was sent, and item 2 is an error message or None
    if email == "": return None, "The email can't be empty!"

    try:
        conn = sqlite3.connect(password_db)
        c = conn.cursor()
        c.execute("select email from dglusers where email=? collate nocase",
                  (email,))
        result = c.fetchone()

        if result:
            server = smtplib.SMTP('localhost', 42456)
            #server = smtplib.SMTP_SSL('localhost', 42456)
            #server.login("admin@webtiles.org", "password")
 
            msg = """Someone (hopefully you) has requested to reset the password for your account at crawl.example.org.

If you initiated this request, please click the following link to reset your password.

    <Link here>

If you did not request this, you don't need to do anything. Your account is safe."""
            server.sendmail("admin@webtiles.org", email, msg)
            server.quit()

            return True, None

        return None, None
    finally:
        if c: c.close()
        if conn: conn.close()
