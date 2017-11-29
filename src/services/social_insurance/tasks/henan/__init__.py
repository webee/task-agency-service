import  base64
str1='410105198801200097'
str2='RvVFH90UwwkAZBmSclHxDw=='
s1 = base64.b64encode(str1)
s2 = base64.decodestring(str2)
print (s1,s2)
