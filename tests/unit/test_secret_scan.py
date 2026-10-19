from scripts.secret_scan import credential_match

def test_short_password_natural_data_is_not_credential_assignment():
    v={'ADMIN_PASSWORD':'4321'}
    assert credential_match(b'Port 4321 and town code 54321 are public metadata.',v) is None
    assert credential_match(b'ADMIN_PASSWORD=4321',v)=='ADMIN_PASSWORD'
    assert credential_match(b'{"password":"4321"}',v)=='ADMIN_PASSWORD'
    assert credential_match(b"password = '4321'",v)=='ADMIN_PASSWORD'

def test_opaque_credentials_are_always_rejected():
    assert credential_match(b'source token MOCK-OPAQUE-CREDENTIAL',{'TYPESAFE_API_KEY':'MOCK-OPAQUE-CREDENTIAL'})=='TYPESAFE_API_KEY'
    assert credential_match(b'MOCK-LONG-PASSWORD',{'ADMIN_PASSWORD':'MOCK-LONG-PASSWORD'})=='ADMIN_PASSWORD'
