import requests
import os
import secrets
import hashlib
import base64
from dotenv import load_dotenv

load_dotenv()

# Almacena temporalmente el code_verifier PKCE entre el envío del OTP y el callback
_current_code_verifier = None


def _generate_pkce_pair():
    """Genera code_verifier y code_challenge para PKCE"""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    return code_verifier, code_challenge


class User:
    def __init__(self, data):
        self.id = data.get('id')
        self.email = data.get('email')


class Session:
    def __init__(self, user_data, access_token, refresh_token=""):
        self.user = User(user_data)
        self.access_token = access_token
        self.refresh_token = refresh_token


class SupabaseAuthClient:

    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    def sign_in_with_otp(self, credentials):
        """Enviar magic link con PKCE flow"""
        global _current_code_verifier
        code_verifier, code_challenge = _generate_pkce_pair()
        _current_code_verifier = code_verifier

        endpoint = f"{self.url}/auth/v1/otp"
        payload = {
            "email": credentials["email"],
            "create_user": True,
            "redirect_to": "http://localhost:3000",
            "code_challenge": code_challenge,
            "code_challenge_method": "s256"
        }
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al enviar magic link: {str(e)}")

    def exchange_code_for_session(self, code):
        """Intercambiar el ?code= de PKCE por access_token y crear sesión"""
        import streamlit as st
        global _current_code_verifier

        if not _current_code_verifier:
            raise Exception("No hay code_verifier disponible. Solicita un nuevo Magic Link.")

        endpoint = f"{self.url}/auth/v1/token?grant_type=pkce"
        payload = {
            "auth_code": code,
            "code_verifier": _current_code_verifier
        }
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al intercambiar código: {str(e)}")

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token", "")
        user_data = data.get("user")

        if not access_token or not user_data:
            raise Exception("Respuesta inválida de Supabase al intercambiar código")

        session = Session(user_data, access_token, refresh_token)
        st.session_state['supabase_session'] = session
        _current_code_verifier = None
        return session

    def set_session_from_token(self, access_token, refresh_token=""):
        """Verificar access_token directamente y crear sesión"""
        import streamlit as st
        user_data = self._get_user(access_token)
        if user_data:
            session = Session(user_data, access_token, refresh_token)
            st.session_state['supabase_session'] = session
            return session
        return None

    def _get_user(self, access_token):
        endpoint = f"{self.url}/auth/v1/user"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {access_token}"
        }
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def get_session(self):
        import streamlit as st
        return st.session_state.get('supabase_session', None)

    def sign_out(self):
        import streamlit as st
        st.session_state.pop('supabase_session', None)


class SupabaseTableClient:

    def __init__(self, url, key, table_name):
        self.url = url
        self.key = key
        self.table_name = table_name
        self._filter = None
        self._order = None
        self._delete = False
        self._columns = "*"
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def select(self, columns="*"):
        self._columns = columns
        return self

    def insert(self, data):
        self._insert_data = data
        return self

    def eq(self, column, value):
        self._filter = (column, value)
        return self

    def order(self, column, desc=False):
        self._order = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def delete(self):
        self._delete = True
        return self

    def execute(self):
        endpoint = f"{self.url}/rest/v1/{self.table_name}"

        if hasattr(self, '_insert_data'):
            response = requests.post(endpoint, json=self._insert_data, headers=self.headers, timeout=10)
            if not response.ok:
                raise Exception(f"Supabase error {response.status_code}: {response.text}")
            response.raise_for_status()

            class Response:
                def __init__(self, d):
                    self.data = d
            return Response(response.json())

        params = {"select": self._columns}

        if self._filter:
            col, val = self._filter
            params[col] = f"eq.{val}"

        if self._order:
            params['order'] = self._order

        if self._delete:
            del_params = {}
            if self._filter:
                col, val = self._filter
                del_params[col] = f"eq.{val}"
            response = requests.delete(endpoint, headers=self.headers, params=del_params, timeout=10)
            response.raise_for_status()

            class Response:
                def __init__(self):
                    self.data = []
            return Response()

        response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        class Response:
            def __init__(self, d):
                self.data = d
        return Response(response.json())


class CustomSupabaseClient:

    def __init__(self, url, key):
        self.supabase_url = url
        self.supabase_key = key
        self.auth = SupabaseAuthClient(url, key)

    def table(self, table_name):
        return SupabaseTableClient(self.supabase_url, self.supabase_key, table_name)


def create_custom_client():
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    return CustomSupabaseClient(url, key)
