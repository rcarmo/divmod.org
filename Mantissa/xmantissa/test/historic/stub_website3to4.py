# -*- test-case-name: xmantissa.test.historic.test_website3to4 -*-

from axiom.userbase import LoginSystem
from axiom.test.historic.stubloader import saveStub

from axiom.plugins.mantissacmd import Mantissa

from xmantissa.website import WebSite

cert = (
    '-----BEGIN CERTIFICATE-----\n'
    'MIICmjCCAgMCBACFAjkwDQYJKoZIhvcNAQEEBQAwgZMxCzAJBgNVBAYTAlVTMRMw\n'
    'EQYDVQQDEwpkaXZtb2QuY29tMREwDwYDVQQHEwhOZXcgWW9yazETMBEGA1UEChMK\n'
    'RGl2bW9kIExMQzERMA8GA1UECBMITmV3IFlvcmsxITAfBgkqhkiG9w0BCQEWEnN1\n'
    'cHBvcnRAZGl2bW9kLm9yZzERMA8GA1UECxMIU2VjdXJpdHkwHhcNMDgwMjIwMjEy\n'
    'NDExWhcNMDkwMjE5MjEyNDExWjCBkzELMAkGA1UEBhMCVVMxEzARBgNVBAMTCmRp\n'
    'dm1vZC5jb20xETAPBgNVBAcTCE5ldyBZb3JrMRMwEQYDVQQKEwpEaXZtb2QgTExD\n'
    'MREwDwYDVQQIEwhOZXcgWW9yazEhMB8GCSqGSIb3DQEJARYSc3VwcG9ydEBkaXZt\n'
    'b2Qub3JnMREwDwYDVQQLEwhTZWN1cml0eTCBnzANBgkqhkiG9w0BAQEFAAOBjQAw\n'
    'gYkCgYEA3ucaT8gUB7BEp2dfRulWBRT6tTDELA7sJzyk+12E1vxQppJDzwG8VgSj\n'
    'sOl8Jw0qnUb/Qoe96UlA8hDYBbmwz0CCvVRSj+1GYj6Ka8NeheME2RU3/benLbyL\n'
    'S7HUQ93Mqs3VWrlv2lMbgp29njwJqvqMRt8JGB1ql8xUDSLw4kcCAwEAATANBgkq\n'
    'hkiG9w0BAQQFAAOBgQAXxMBJu+VkazQSuOnIn5Ewug2tHmf0sxT7FkcB2nEviQ7U\n'
    'e2bb95IL9XqkO0yKEbJ5K8T8SyXW9VNUATce4JO6NNikyVCZzV1dG2+ATDBaaVHK\n'
    'S2Beh1p6boFvv0+k2qZ/9JmJYVx4l1xPavc70x95rR2E0kuwhyw4miHpSMqfpA==\n'
    '-----END CERTIFICATE-----\n'
    '-----BEGIN RSA PRIVATE KEY-----\n'
    'MIICXQIBAAKBgQDe5xpPyBQHsESnZ19G6VYFFPq1MMQsDuwnPKT7XYTW/FCmkkPP\n'
    'AbxWBKOw6XwnDSqdRv9Ch73pSUDyENgFubDPQIK9VFKP7UZiPoprw16F4wTZFTf9\n'
    't6ctvItLsdRD3cyqzdVauW/aUxuCnb2ePAmq+oxG3wkYHWqXzFQNIvDiRwIDAQAB\n'
    'AoGAG/YHgeyKPrCo3AsGk6GfjcGk9WeppBE3JHDiDToc+M7r2wlMAkKoem3Yjs+r\n'
    'KEbpipMmYBUhCIuM3xCn2IgDmq/9rC+mDmEu7mEvL0Rnl5Ns6m/uw61kYKDAghYg\n'
    'K7lD3jlAT/a9I8wB2UO9F6p8166YERU736Qa4GUle4l8irECQQD0V6ZbbW1o5j5s\n'
    'IUzhVvBr/flWabpMJ9Vw3eLy695iFjgx+5W0nD+JK1ny8MiwCRsjoRTXldHhdaod\n'
    '8VbPz/QJAkEA6YmX6XksIb8JUYFtPk0WodQmz51qzo0jol3COL/rXuPVkTcesyTM\n'
    '61S7WSv0G6pMqE9xw0llMBON7Pr24N/XzwJBALW+eFvrEgWDtQyi3FeEXkJFX+/5\n'
    'pnu86VMRiByeewREeLoc4ya7TbsOxtIgbXYa39fpmeIda0ajSc0J1UOv71kCQQCO\n'
    'q20vx8PrNc7WiTAY4HVUFcxEB5Ipb1X2qjqt+qkrBhsBpN/PZ0r89X2iw1RU1lwQ\n'
    'csA4Io17qmaJAORziqxHAkAb2zin9SzS58+X55pGVp8PwhGLmm9cGH/DtWVSIAl2\n'
    'q3pqCmcxnimc+IYJJlY6dkk7jtnIVTWz3B9XUOtKGEYF\n'
    '-----END RSA PRIVATE KEY-----\n')

def createDatabase(store):
    """
    Initialize the given Store for use as a Mantissa webserver.
    """
    Mantissa().installSite(store, u'')
    ws = store.findUnique(WebSite)
    ws.portNumber = 8088
    ws.securePortNumber = 6443
    ws.certificateFile = 'path/to/cert.pem'
    certPath = store.dbdir.child('path').child('to').child('cert.pem')
    certPath.parent().makedirs()
    fObj = certPath.open('w')
    fObj.write(cert)
    fObj.close()
    ws.httpLog = 'path/to/httpd.log'
    ws.hitCount = 123

    loginSystem = store.findUnique(LoginSystem)
    account = loginSystem.addAccount(u'testuser', u'localhost', None)
    subStore = account.avatars.open()
    WebSite(store=subStore, hitCount=321).installOn(subStore)


if __name__ == '__main__':
    saveStub(createDatabase, 7617)
