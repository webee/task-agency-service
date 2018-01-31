import hashlib
m = hashlib.md5()
m.update(str('123654').encode(encoding="utf-8"))
hashpsw = m.hexdigest()

print(hashpsw)

print('355c0bec3c61dbac')   