import bcrypt

test_hashes = {
    'rohit@gmail.com': b'$2b$10$9Zyk6uSGuCv8b.JLADKzce7KPE.vwnkQDIWTJ5PXEf0XzekkNzT0K',
    'romilpolara49@gmail.com': b'$2b$12$sRgIvOnDMGFMtIQAlaogaujHpYsFtUMdi4bVg2duHgc5IESXLLW3G'
}

def test_password(password: str):
    pwd_bytes = password.encode('utf-8')
    print(f"Testing password: '{password}'")
    for email, hash_bytes in test_hashes.items():
        try:
            if bcrypt.checkpw(pwd_bytes, hash_bytes):
                print(f"MATCH FOUND! Email: {email}, Password: '{password}'")
        except ValueError as e:
            pass

test_password("+911234567891")
test_password("1234567891")
test_password("+912323232323")
test_password("2323232323")
test_password("12345678918")
test_password("12345678911")
test_password("12345678918!")
