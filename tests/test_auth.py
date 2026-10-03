import threading, unittest, urllib.request, urllib.error
from http.server import ThreadingHTTPServer
import auth
import serve_private as app

class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.password='temporary-test-password'
        app.PASSWORD_HASH=auth.password_hash(cls.password)
        app.SESSION_SECRET='test-session-secret-that-is-only-for-tests'
        app.COOKIE_SECURE=False
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.PrivateHandler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls): cls.server.shutdown();cls.server.server_close()
    def test_private_routes_require_session(self):
        for path in ['/', '/state.json','/guide.html']:
            r=urllib.request.urlopen(self.base+path)
            if path=='/api/state': self.fail('API must reject unauthenticated access')
            self.assertEqual(r.url,self.base+'/login')
    def test_api_denies_unauthenticated_requests(self):
        for path in ['/api/state','/api/scan']:
            request=urllib.request.Request(self.base+path,data=b'{}' if path.endswith('scan') else None,headers={'Origin':self.base})
            with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(request)
            self.assertEqual(cm.exception.code,401)
    def test_session_signature_and_authenticated_api(self):
        token=auth.issue_session(app.SESSION_SECRET)
        self.assertFalse(auth.valid_session(auth.COOKIE+'='+token+'x',app.SESSION_SECRET))
        r=urllib.request.urlopen(urllib.request.Request(self.base+'/api/state',headers={'Cookie':auth.COOKIE+'='+token}))
        self.assertEqual(r.status,200)
    def test_password_verification(self):
        self.assertTrue(auth.verify_password(self.password,app.PASSWORD_HASH))
        self.assertFalse(auth.verify_password('wrong',app.PASSWORD_HASH))
    def test_cross_origin_login_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(urllib.request.Request(self.base+'/login',data=b'password=wrong',headers={'Origin':'https://other.example'}))
        self.assertEqual(cm.exception.code,403)
if __name__=='__main__':unittest.main()
