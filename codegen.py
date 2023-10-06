import os

code = os.urandom(999).hex()
f = open("code.txt", "w")
f.write(code)
f.close()
