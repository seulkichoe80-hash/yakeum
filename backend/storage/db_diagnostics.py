"""Allowlisted DB diagnostics: inspect locally, never log exceptions or connection data."""
import logging
import socket

log=logging.getLogger(__name__)
PHASES=frozenset({'CONFIG','CONNECT','INITIALIZE','QUERY','COMMIT'})
CATEGORIES=frozenset({
    'CONFIGURATION','DNS','NETWORK_TIMEOUT','NETWORK_UNREACHABLE','AUTHENTICATION',
    'SSL_CERTIFICATE','SSL_NEGOTIATION','SCHEMA_PERMISSION','SCHEMA_INITIALIZATION',
    'SCHEMA_VERSION','PERMISSION','DATABASE_SELECTION','CONNECTION_LIMIT',
    'CONSTRAINT','DATABASE_TIMEOUT','CONNECTION_UNKNOWN','QUERY_FAILED','COMMIT_FAILED',
})


def classify_db_error(error,phase):
    """SQLSTATE first; libpq connection text is heuristic input only, never output."""
    state=getattr(error,'sqlstate',None)
    if state in {'28P01','28000'}:return 'AUTHENTICATION'
    if state=='42501':return 'SCHEMA_PERMISSION' if phase=='INITIALIZE' else 'PERMISSION'
    if state=='3D000':return 'DATABASE_SELECTION'
    if state=='53300':return 'CONNECTION_LIMIT'
    if state in {'57014','55P03'}:return 'DATABASE_TIMEOUT'
    if state in {'23505','23503','23502','23514','23P01'}:return 'CONSTRAINT'
    if phase=='CONNECT':
        if isinstance(error,socket.gaierror):return 'DNS'
        # libpq often supplies no SQLSTATE before authentication completes.
        # Never include this text (or exception args/diag/traceback) in a log record.
        text=str(error).lower()
        if any(s in text for s in ('certificate verify failed','certificate verification failed',
                'root certificate file','could not read root certificate','server certificate',
                'certificate has expired','certificate is not yet valid','self-signed certificate')):
            return 'SSL_CERTIFICATE'
        if any(s in text for s in ('could not translate host name','could not resolve',
                'failed to resolve host','name or service not known','temporary failure in name resolution',
                'nodename nor servname')):return 'DNS'
        if any(s in text for s in ('password authentication failed','authentication failed',
                'tenant or user not found','invalid credentials')):return 'AUTHENTICATION'
        if any(s in text for s in ('invalid connection option','invalid connection string',
                'missing "="','invalid integer value','invalid uri')):return 'CONFIGURATION'
        if any(s in text for s in ('timeout expired','timed out','connection timeout')):return 'NETWORK_TIMEOUT'
        if any(s in text for s in ('connection refused','network is unreachable','no route to host',
                'connection reset by peer','server closed the connection unexpectedly')):return 'NETWORK_UNREACHABLE'
        if any(s in text for s in ('ssl error','ssl connection','server does not support ssl',
                'tls handshake')):return 'SSL_NEGOTIATION'
        return 'CONNECTION_UNKNOWN'
    if phase=='INITIALIZE':return 'SCHEMA_INITIALIZATION'
    if phase=='COMMIT':return 'COMMIT_FAILED'
    return 'QUERY_FAILED'


def report_db_failure(category,phase):
    # Even callers cannot accidentally send arbitrary diagnostics to the logger.
    if category not in CATEGORIES or phase not in PHASES:
        raise ValueError('Unsupported diagnostic classification')
    log.warning('YAKEUM_DB_FAILURE category=%s phase=%s',category,phase)
