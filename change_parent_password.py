from salt import SALT
import hashlib
import sys

if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        print("USAGE: change_parent_password.py [new_password]")
    else:
        file = open("parent_password", "wb")
        file.write(hashlib.pbkdf2_hmac("sha256", args[1].encode("utf-8"), SALT, 10000))
        file.close()
