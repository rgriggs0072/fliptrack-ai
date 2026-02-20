"""
Snowflake Connection Utility
============================
Handles database connections using RSA key pair authentication.
"""

import streamlit as st
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

@st.cache_resource(ttl=3600)  # Cache for 1 hour (3600 seconds)
def get_connection():
    """
    Create and cache Snowflake connection.
    Uses RSA key pair authentication from secrets.toml
    Supports both file path (local dev) and embedded key (cloud deployment)
    Connection is cached for 1 hour to prevent token expiration issues.
    """
    
    # Check if private key is embedded in secrets or file path
    if "private_key" in st.secrets["snowflake"]:
        # Cloud deployment - key is embedded in secrets
        private_key_str = st.secrets["snowflake"]["private_key"]
        p_key = serialization.load_pem_private_key(
            private_key_str.encode(),
            password=None,
            backend=default_backend()
        )
    else:
        # Local development - key is in file
        with open(st.secrets["snowflake"]["private_key_path"], "rb") as key_file:
            p_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
                backend=default_backend()
            )
    
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Connect to Snowflake
    conn = snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        private_key=pkb,
        warehouse=st.secrets["snowflake"]["warehouse"],
        role=st.secrets["snowflake"]["role"]
    )
    
    return conn


def get_client_database():
    """
    Get the database name for the current logged-in client.
    Returns the database and schema names.
    """
    if 'user_info' not in st.session_state:
        return None, None
    
    return (
        st.session_state.user_info.get('database_name'),
        st.session_state.user_info.get('schema_name')
    )


def switch_to_client_database(conn):
    """
    Switch connection to the current client's database.
    """
    database, schema = get_client_database()
    
    if database and schema:
        cursor = conn.cursor()
        cursor.execute(f"USE DATABASE {database}")
        cursor.execute(f"USE SCHEMA {schema}")
        cursor.close()
        return True
    
    return False


def execute_query(query, params=None):
    """
    Execute a query and return results as a list of dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        # Fetch all results
        results = cursor.fetchall()
        
        # Convert to list of dicts
        return [dict(zip(columns, row)) for row in results]
    
    finally:
        cursor.close()


def execute_insert(query, params=None):
    """
    Execute an INSERT/UPDATE/DELETE query.
    Returns True if successful.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return True
    
    except Exception as e:
        st.error(f"Database error: {e}")
        return False
    
    finally:
        cursor.close()
